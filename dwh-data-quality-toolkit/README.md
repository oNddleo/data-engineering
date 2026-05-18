# dwh-data-quality-toolkit

Composable, pure-Python data-quality checks for VN data warehouses.
Twelve bundled validators — seven generic + five VN-specific — wired
into a registry-driven Suite runner with severity-aware quarantine
mode. Pairs with every other repo in this catalogue (Shopee scrapers,
EVN meters, AQI stations, CLV segmenter, …) — validate the data
*before* you load it.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Twelve bundled checks** spanning structural (`not_null`,
   `unique`, `in_set`, `regex`, `range_int`, `dtype_int`, `dtype_str`)
   and VN-domain (`cccd`, `mst`, `vn_phone`, `vn_bank_account`,
   `vn_postal_code`).
2. **Suite** = JSON-serialisable bundle of `(check, column, severity, args)`
   triples. Store next to your DDL, reload on each batch.
3. **Run** the suite against a JSONL rowset → list of `CheckResult`s
   with row-level failure detail.
4. **Quarantine mode** splits the rowset into `good.jsonl` /
   `bad.jsonl` based on ERROR-severity failures. WARNING failures
   log but don't quarantine.
5. **CI-friendly exit codes**: `0` when no ERROR failures, `2` when
   any. WARNING-only batches still pass.

## VN-specific checks

| Check                | What it validates                                                       |
| -------------------- | ----------------------------------------------------------------------- |
| ``cccd``             | 12-digit Citizen Identity Card per Circular 07/2016/TT-BCA (province + gender-century + YY + sequence) |
| ``mst``              | 10- or 13-digit tax code with weighted-sum-mod-11 checksum on the primary 10 (matches `vn-tax-invoice-validator`) |
| ``vn_phone``         | Mobile prefixes 03/05/07/08/09 (9 digits) or landline 02x (9 digits), with or without ``+84`` |
| ``vn_bank_account``  | 8 — 19 digits (loosest reasonable; bank-specific tightening is caller's job) |
| ``vn_postal_code``   | 5-digit VietPost code per Decision 2475/QĐ-BTTTT with valid province prefix |

Validated against four real public Vietnamese tax codes (Vietcombank
`0100109106`, FPT `0301442379`, Mobile World `0301448243`, Vietjet
`0309532909`) — these all pass. Mutated check digits fail.

## Components

| Module                  | Role                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `dqkit.schema`          | `Check` Protocol, `CheckResult`, `CheckSpec`, `Suite`, `Severity`   |
| `dqkit.checks_generic`  | `not_null`, `unique`, `in_set`, `regex`, `range_int`, `dtype_int`, `dtype_str` |
| `dqkit.checks_vn`       | `cccd`, `mst`, `vn_phone`, `vn_bank_account`, `vn_postal_code`      |
| `dqkit.runner`          | `run_suite`, `quarantine_rows`, `summarise`, `list_checks`          |
| `dqkit.simulator`       | Synthetic customer rowset with 10 injectable defects                |
| `dqkit.io_jsonl`        | JSONL codec for rows + results; JSON codec for suites               |
| `dqkit.cli`             | `dqkit info \| checks \| simulate \| make-suite \| run`             |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
dqkit info                                        # version + registered checks
dqkit checks                                      # list registered check names
dqkit simulate --rows 50 --defect-fraction 0.30 \
               --seed 7 --output ./customers.jsonl
dqkit make-suite --output ./suite.json            # starter suite for customer schema
dqkit run --input ./customers.jsonl --suite ./suite.json \
          --results-output ./results.jsonl \
          --quarantine-dir ./quarantine            # → good.jsonl + bad.jsonl
```

Sample `run` output on 50 rows with 30% defects:

```json
{
  "n_checks": 9,
  "n_passed": 2,
  "n_failed": 7,
  "by_severity": {"ERROR": 6, "WARNING": 1},
  "per_check": [
    {"check": "not_null",        "column": "customer_id",      "severity": "ERROR",   "n_rows": 50, "n_failed": 0},
    {"check": "unique",          "column": "customer_id",      "severity": "ERROR",   "n_rows": 50, "n_failed": 1},
    {"check": "cccd",            "column": "cccd",             "severity": "ERROR",   "n_rows": 50, "n_failed": 2},
    {"check": "mst",             "column": "mst",              "severity": "ERROR",   "n_rows": 50, "n_failed": 2},
    {"check": "vn_phone",        "column": "phone",            "severity": "WARNING", "n_rows": 50, "n_failed": 0},
    {"check": "vn_bank_account", "column": "bank_account",     "severity": "ERROR",   "n_rows": 50, "n_failed": 3},
    {"check": "vn_postal_code",  "column": "postal_code",      "severity": "WARNING", "n_rows": 50, "n_failed": 4},
    {"check": "in_set",          "column": "tier",             "severity": "ERROR",   "n_rows": 50, "n_failed": 4},
    {"check": "range_int",       "column": "credit_limit_vnd", "severity": "ERROR",   "n_rows": 50, "n_failed": 4}
  ]
}
```

CLI exit code: 0 on no ERROR failures, 2 when any. CI pipelines
consume this directly.

## Library

```python
from dqkit.runner import run_suite, quarantine_rows, summarise
from dqkit.schema import CheckSpec, Severity, Suite

rows = [
    {"customer_id": "C-001", "cccd": "001201123456", "mst": "0100109106"},
    {"customer_id": "C-002", "cccd": "BAD",          "mst": "0100109107"},  # both bad
]
suite = Suite(name="customers", specs=(
    CheckSpec(check="not_null", column="customer_id", severity=Severity.ERROR),
    CheckSpec(check="cccd",     column="cccd",        severity=Severity.ERROR),
    CheckSpec(check="mst",      column="mst",         severity=Severity.ERROR),
))
results = run_suite(rows, suite)
print(summarise(results))

good, bad = quarantine_rows(rows, results)   # row 1 → bad; row 0 → good
```

## Key design decisions

- **Check is a Protocol, not a base class.** Production callers add
  in-house checks by writing a callable that matches the signature
  — no inheritance, no subclass-registration ceremony.
- **Factories take parameters once and return a configured Check.**
  The Suite then references checks by name + args; checks themselves
  are stateless callables. This is what makes the `Suite` JSON-
  serialisable and version-controllable.
- **`None` and empty-string handling is uniform**: `not_null` flags
  them; every other check skips them silently. Pair with `not_null`
  if presence is required.
- **`bool` is rejected by `dtype_int`** even though `True` is an `int`
  subclass — this catches a real DW bug where JSON booleans get
  silently loaded into integer columns.
- **WARNING vs ERROR.** ERRORs quarantine the row; WARNINGs log
  only. The CI exit code (`0` vs `2`) follows ERROR-only. Production
  pipelines split alerting channels: ERRORs page on-call; WARNINGs
  hit the daily dashboard.
- **JSON-only Suites — no Python source.** Storing suites as data
  means they live in source control next to the schema, can be diffed
  cleanly, and don't require a Python import to inspect.
- **The MST check shares the algorithm** with `vn-tax-invoice-validator`
  (the formula special-cases ``mod == 0 → 0`` and otherwise
  ``10 - mod`` — no carve-outs). Verified against four real public
  MSTs.

## Quality

```bash
make test       # 87 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **87 tests**, 0 failing; 6 Hypothesis properties (`not_null`
  failure count matches null + empty, `unique` failure count equals
  duplicate count, `range_int` failure count matches out-of-band
  count, computed MST check digit is always accepted, any valid VN
  mobile prefix passes, non-mobile prefixes are rejected).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `dqkit` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
