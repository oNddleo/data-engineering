# csv-schema-inference-toolkit

**Infer the schema** of a raw CSV file — column types, nullability,
cardinality, value-distribution samples — and **emit downstream
schemas** in Avro 1.11, JSON Schema draft-07, or
``@dataclass(frozen=True, slots=True)`` Python code. **VN-locale
aware**: handles dd/MM/yyyy dates, decimal commas (``1.500.000,00``),
Vietnamese boolean tokens (``Có`` / ``Không``).

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Sniffs the delimiter** — tries `,`, `;`, `\t`, `|` and picks
   the one producing the most consistent column count.
2. **Sniffs the header** — declares the first row a header if every
   cell is non-empty and either row 2 contains typed values, or
   row 1 cells look like identifier names (e.g. `customer_name`).
3. **Infers per-column type** in order of specificity:
   `BOOL → INT → DATE → DATETIME → DECIMAL → FLOAT → STRING`.
   Every non-empty cell must parse as the chosen type.
4. **Tracks per-column metadata** — nullability, distinct
   cardinality (capped at 1000), up to 5 representative examples,
   min/max for numeric and temporal types, the detected format
   string for dates (`dd/MM/yyyy` or `yyyy-mm-dd`).
5. **Emits downstream schemas** in three formats, deterministic and
   ready for ingest into a warehouse / message bus / data class.

## Type detection coverage

| Pattern                       | Detected as | Format string |
| ----------------------------- | ----------- | ------------- |
| `42`, `1.234.567`, `1,234,567`| INT         | —             |
| `1.5`, `-2.75`, `1e-3`        | FLOAT       | —             |
| `1.500.000,00`, `50,75`       | DECIMAL     | —             |
| `true`/`false`/`yes`/`no`/`Có`/`Không`/`1`/`0` | BOOL | — |
| `17/05/2026`                  | DATE        | `dd/MM/yyyy`  |
| `2026-05-17`                  | DATE        | `yyyy-mm-dd`  |
| `2026-05-17T09:00:00+07:00`   | DATETIME    | `iso8601`     |
| anything else                 | STRING      | —             |

A single non-parseable cell disqualifies the candidate type; if
every type fails, the column falls back to STRING.

## Schema projections

| ColumnType | Avro 1.11                              | JSON Schema       | Python dataclass     |
| ---------- | -------------------------------------- | ----------------- | -------------------- |
| INT        | `"long"`                               | `"integer"`       | `int`                |
| FLOAT      | `"double"`                             | `"number"`        | `float`              |
| DECIMAL    | `bytes` + `decimal` logical (P=18 S=4) | `"string"`        | `str` (or `Decimal`) |
| BOOL       | `"boolean"`                            | `"boolean"`       | `bool`               |
| DATE       | `int` + `date` logical                 | `"string"` `date` | `datetime.date`      |
| DATETIME   | `long` + `timestamp-millis` logical    | `"string"` `date-time` | `datetime.datetime` |
| STRING     | `"string"`                             | `"string"`        | `str`                |

Nullable columns become Avro `["null", T]` unions, JSON Schema
`[T, "null"]` type arrays, and `T | None = None` defaults in
Python dataclasses (required-first ordering preserved for
positional init).

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `csvinf.schema`    | `ColumnType`, `InferredColumn`, `InferredSchema` frozen dataclasses |
| `csvinf.parsers`   | `try_int / try_float / try_decimal / try_bool / try_date / try_datetime` (VN-locale) |
| `csvinf.reader`    | Delimiter + header sniffing, full stream read                       |
| `csvinf.infer`     | The inference engine — walks rows, votes per candidate type         |
| `csvinf.emit`      | `emit_avro` / `emit_json_schema` / `emit_dataclass`                 |
| `csvinf.simulator` | Seeded synthetic VN-flavoured CSV generator                         |
| `csvinf.io_jsonl`  | Type-checked JSONL codec for inferred schemas                       |
| `csvinf.cli`       | `csvinf info \| simulate \| infer \| emit \| summary`               |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
csvinf info
csvinf simulate --rows 100 --seed 7 --output orders.csv
csvinf infer    --input orders.csv --output schema.json --show
csvinf emit     --input orders.csv --format avro --name Order
csvinf emit     --input orders.csv --format json-schema --name Order
csvinf emit     --input orders.csv --format dataclass --name Order
csvinf summary  --input orders.csv
```

Sample synthetic CSV (`csvinf simulate --rows 3 --seed 7`):

```
order_id,customer_name,email,amount_vnd,qty,is_paid,created_date,signed_at,note
1,Đặng Thị F,user0000@example.vn,"1.315.414,50",1,Có,22/06/2026,2026-06-22T16:06:23,freight #932
2,Nguyễn Văn A,user0001@example.vn,"770.977,55",7,Có,16/05/2026,2026-05-16T09:35:27,freight #580
3,Phạm Thị D,user0002@example.vn,"4.940.532,07",10,Không,04/05/2026,2026-05-04T11:02:35,freight #297
```

Sample `infer --show`:

```
source:    orders.csv
delimiter: ','
header:    True
rows:      50
column                   type        null%   card fmt
order_id                 INT          0.0%     50
customer_name            STRING      10.0%      8
email                    STRING       0.0%     50
amount_vnd               DECIMAL      0.0%     50
qty                      INT          0.0%     10
is_paid                  BOOL         0.0%      2
created_date             DATE         0.0%     35 dd/MM/yyyy
signed_at                DATETIME     0.0%     50 iso8601
note                     STRING       2.0%     49
```

Sample `emit --format avro`:

```json
{
  "type": "record",
  "name": "Order",
  "fields": [
    { "name": "order_id", "type": "long" },
    { "name": "customer_name", "type": ["null", "string"], "default": null },
    { "name": "email", "type": "string" },
    { "name": "amount_vnd", "type": {
        "type": "bytes", "logicalType": "decimal",
        "precision": 18, "scale": 4
    }},
    { "name": "qty", "type": "long" },
    { "name": "is_paid", "type": "boolean" },
    { "name": "created_date", "type": {"type": "int", "logicalType": "date"} },
    { "name": "signed_at", "type": {"type": "long", "logicalType": "timestamp-millis"} },
    { "name": "note", "type": ["null", "string"], "default": null }
  ]
}
```

Sample `emit --format dataclass`:

```python
"""Auto-generated by csvinf.emit.emit_dataclass."""

from __future__ import annotations

from datetime import date
from datetime import datetime

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Order:
    """One row, schema inferred by csvinf."""

    order_id: int
    email: str
    amount_vnd: str
    qty: int
    is_paid: bool
    created_date: date
    signed_at: datetime
    customer_name: str | None = None
    note: str | None = None
```

## Library

```python
from csvinf.emit   import emit_avro, emit_dataclass, emit_json_schema
from csvinf.infer  import infer_schema
from csvinf.parsers import try_decimal, try_date

schema = infer_schema(open("orders.csv").read(), source_name="orders.csv")
for col in schema.columns:
    print(col.name, col.type.value, col.nullable, col.cardinality, col.examples)

avro_bytes      = emit_avro(schema, record_name="Order")
json_schema_str = emit_json_schema(schema, title="Order")
dataclass_code  = emit_dataclass(schema, class_name="Order")

# VN-locale parsers exposed directly:
assert try_decimal("1.500.000,00") == "1500000.00"
assert try_date("17/05/2026") == __import__("datetime").date(2026, 5, 17)
```

## Key design decisions

- **VN-locale first.** Decimal commas (`1.500.000,00`) and dd/MM/yyyy
  dates show up in every VN bank export, invoice, and government
  CSV. Treating them as STRING would route real money into the wrong
  warehouse type.
- **Specificity-ordered inference.** BOOL → INT → DATE → DATETIME →
  DECIMAL → FLOAT → STRING. A column of `0`/`1` is BOOL (every cell
  matches); a column of `0`/`1`/`42` is INT (one cell forces fall-
  through). STRING is the always-safe fallback.
- **Cardinality cap.** Distinct counting stops at `MAX_CARDINALITY
  = 1000` and returns `MAX_CARDINALITY + 1` for "many". This keeps
  inference O(n + bounded) for files of any size without OOMing.
- **Required-first dataclass ordering.** Required fields render
  before nullable defaults so positional `Order(1, "Alice", ...)`
  calls still work in downstream code.
- **No external deps.** Pure stdlib — `csv`, `re`, `json`,
  `dataclasses`, `datetime`. Drop-in for any data-engineering
  bootstrap (no NumPy or Pandas required to onboard a new dataset).
- **Deterministic emitters.** Same schema → same bytes. Safe to
  commit emitted Avro / JSON Schema / dataclass code to git as
  golden files for review.

## Quality

```bash
make test       # 125 tests + 11 Hypothesis properties
make type       # mypy --strict
make lint
```

- **125 tests**, 0 failing; 11 Hypothesis properties (int round-trip
  through `try_int`; float round-trip; ISO date round-trip; bool
  tokens always parse; alpha strings never parse as int/float/decimal;
  int columns always detected; bool columns always detected; alpha
  string columns always STRING; Avro emit deterministic; emitted
  Avro is valid JSON; emitted dataclass code always compiles;
  emitted JSON Schema is always valid).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `csvinf` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
