# Changelog

## [0.1.0] — 2026-05-18

### Added
- `ColumnType` enum with seven values (INT / FLOAT / DECIMAL / BOOL /
  DATE / DATETIME / STRING).
- `InferredColumn` frozen-slots dataclass with `name`, `type`,
  `nullable`, `n_rows`, `n_non_null`, `cardinality` (capped at
  `MAX_CARDINALITY = 1000`), `examples` (up to 5 distinct), `min_value`,
  `max_value`, `detected_format`. Validation enforces non-negative
  counts and `n_non_null <= n_rows`. Properties `null_fraction` and
  `is_high_cardinality`.
- `InferredSchema` frozen-slots dataclass with `source_name`,
  `delimiter`, `has_header`, `n_rows_scanned`, `columns`. Validates
  duplicate column names; offers `column(name)` lookup.
- `csvinf.parsers` — strict per-type parsers returning `None` on
  failed parse: `try_int` (plain, VN `1.234.567`, EN `1,234,567`
  thousands separators), `try_float` (EN-locale decimal point),
  `try_decimal` (VN-locale `1.500.000,00` → normalised
  `"1500000.00"`), `try_bool` (true/false/yes/no/1/0 + VN Có/Không),
  `try_date` (ISO `yyyy-mm-dd` + VN `dd/MM/yyyy`), `try_datetime`
  (ISO-8601 with optional `Z` or `±HH:MM` offset). Helpers
  `detect_date_format` / `detect_datetime_format` return the canonical
  format-string.
- `csvinf.reader` — `sniff_delimiter()` picks from `,`, `;`, `\t`,
  `|` based on column-count consistency. `sniff_has_header()` declares
  a header when row 1 has all non-empty, non-typed cells AND
  (row 2 contains typed values OR every row 1 cell is identifier-like).
  Unicode-aware (recognises VN names like `Tên` / `địa_chỉ`).
  `read(text, max_rows)` returns delimiter + header + rows.
- `csvinf.infer.infer_schema()` — walks the row stream once per
  column, voting per candidate type in order BOOL → INT → DATE →
  DATETIME → DECIMAL → FLOAT → STRING. Computes min/max in natural
  type ordering; STRING is the always-safe fallback.
- `csvinf.emit` — deterministic emitters:
  - `emit_avro()` — Avro 1.11 record schema with logical types for
    DECIMAL (bytes, P=18 S=4), DATE (int + `date`), DATETIME (long
    + `timestamp-millis`). Nullable columns become `["null", T]`
    unions with `default: null`.
  - `emit_json_schema()` — JSON Schema draft-07 object schema with
    `format: "date"` / `format: "date-time"` annotations and
    `examples` carried from inferred values.
  - `emit_dataclass()` — Python `@dataclass(frozen=True, slots=True)`
    source code with required-first field ordering, sanitized
    identifiers (replaces spaces with `_`, prefixes leading digits
    with `_`), `from __future__ import annotations`, and per-type
    imports (`from datetime import date / datetime`).
- `csvinf.simulator.generate()` — seeded VN-flavoured CSV generator
  producing 9-column orders data with INT / DECIMAL / BOOL / DATE /
  DATETIME / STRING types and configurable nullability.
- `csvinf.io_jsonl` — type-checked JSONL codec for `InferredSchema`
  + `InferredColumn`. Rejects bool-as-int and string-as-bool.
- `csvinf.cli` — `csvinf info | simulate | infer | emit | summary`.
- 125 unit tests + 11 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/csv-schema-inference-toolkit-v0.1.0
