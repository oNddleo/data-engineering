# slowly-changing-dimensions-toolkit

Kimball **SCD Type 1 / 2 / 3 / 4 / 6** appliers for data-warehouse
dimension tables, plus a snapshot-diff detector that emits
`INSERT / UPDATE / DELETE` change events. Pure-Python, integer
surrogate keys, deterministic output, zero runtime dependencies.

Use case: a Shopee seller renames their shop, a customer's CCCD
address updates, a product changes category. Pick the SCD type per
attribute, run the toolkit against last night's snapshot vs today's,
and load the result into your DW.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## The five SCD types

| Type | Name             | History kept                              | When to use                                                  |
| ---- | ---------------- | ----------------------------------------- | ------------------------------------------------------------ |
| 1    | Overwrite        | none                                      | attribute change has no analytical value (e.g. typos)        |
| 2    | New row          | full — one row per version                | most common; reporting needs "as-of" state                   |
| 3    | Previous column  | one prior value per tracked attribute     | only the immediate-prior value matters (rare)                |
| 4    | History table    | full — main table + side history table    | hot path stays small; cold history queried separately        |
| 6    | Hybrid (1+2+3)   | full — current attrs + history + previous | get all three views from one schema                          |

A real DW uses *different types* for different attributes on the same
dimension. This toolkit's `apply_type_*` functions take a list of
**tracked attributes** so the same dimension can have a Type-1 timestamp,
a Type-2 shop_name, and a Type-3 region on different columns.

## What it does

1. **Detect**: ``detect(before, after, as_of, tracked_attrs?)`` diffs two
   snapshot dicts → `INSERT / UPDATE / DELETE` change events.
   Untracked-attribute changes are silently skipped (no spurious Type-2
   row on a `last_load_ts` bump — the recurring bug in naive SCD-2 loads).
2. **Apply**: one applier per type, each a pure function over
   ``(state, changes)`` returning the new state. Type-2 / Type-4 / Type-6
   assign monotonically-increasing `surrogate_key`s; the starting value
   is caller-supplied so batches chain cleanly.
3. **Query**: ``type_2_current(state)`` for the as-of-now view;
   ``type_2_history_for(state, natural_key)`` for one entity's full
   version chain sorted by `effective_from`.

## Components

| Module                | Role                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `scdkit.schema`       | `SCDType`, `ChangeKind`, `DimensionRow`, `DimensionChange`, `HIGH_DATE` |
| `scdkit.detect`       | `detect(before, after, as_of, tracked_attrs?)`, `n_changes_by_kind`   |
| `scdkit.appliers`     | `apply_type_1` … `apply_type_6`, `Type2State`, `Type4State`, `Type6State` |
| `scdkit.simulator`    | Seeded synthetic Shopee-seller dimension with realistic churn          |
| `scdkit.io_jsonl`     | Type-checked JSONL codec for snapshots, rows, change events            |
| `scdkit.cli`          | `scdkit info \| simulate \| detect \| apply \| history \| summary`     |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
scdkit info
scdkit simulate --entities 50 --seed 7 --out-dir ./snap
scdkit detect   --before ./snap/before.jsonl --after ./snap/after.jsonl \
                --as-of "2026-05-17T09:00:00+07:00" \
                --tracked-attrs shop_name,tier \
                --output ./changes.jsonl
scdkit apply    --type TYPE_2 --changes ./changes.jsonl \
                --tracked-attrs shop_name,tier --output ./type2.jsonl
scdkit history  --changes ./changes.jsonl --natural-key S-000001
scdkit summary  --before ./snap/before.jsonl --after ./snap/after.jsonl \
                --as-of "2026-05-17T09:00:00+07:00"
```

Sample `detect` output for 30 entities + 10% inserts / 5% deletes / 30% updates:

```
Changes by kind:
  INSERT       3
  UPDATE       9
  DELETE       1
```

Sample `history` output (Type-2 version chain for one seller):

```
  sk from                      to                        current attributes
   1 2026-05-01T09:00:00+07:00 2026-05-09T09:00:00+07:00 NO      {"shop_name":"Shop Sai Gon","tier":"BASIC"}
   2 2026-05-09T09:00:00+07:00 9999-12-31T23:59:59+07:00 YES     {"shop_name":"Shop Sai Gon","tier":"PREFERRED"}
```

## Library

```python
from scdkit.detect    import detect
from scdkit.appliers  import apply_type_2, type_2_current, type_2_empty
from datetime         import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))
now = datetime(2026, 5, 17, 9, 0, tzinfo=VN_TZ)

before = {"S-1": {"shop_name": "Shop Saigon", "tier": "BASIC"}}
after  = {"S-1": {"shop_name": "Shop Saigon", "tier": "PREFERRED"},
          "S-2": {"shop_name": "New Shop",    "tier": "MALL"}}

# Filter to "tier" so a non-tracked `last_load_ts` bump doesn't fire.
changes = detect(before, after, as_of=now, tracked_attrs=["shop_name", "tier"])

state = apply_type_2(type_2_empty(start_surrogate=1), changes)
print(type_2_current(state))     # current row per natural_key
```

## Key design decisions

- **Tracked-attribute filtering** on `detect` is the difference between
  a sensible Type-2 load and a runaway history table. Filter aggressively;
  the toolkit defaults to all-attributes-tracked only as a convenience.
- **All appliers are pure functions**, never mutate their inputs. The
  Hypothesis property suite verifies idempotency across `detect →
  apply → detect(same, same)` cycles.
- **Surrogate keys are integers** assigned monotonically per batch. The
  caller pins `start_surrogate` so chained batches stay collision-free.
  No UUIDs — they're 16× the storage and slower to join.
- **`HIGH_DATE = 9999-12-31`** for the open-ended `effective_to` on the
  current Type-2 row. Common DW convention; avoids needing to handle
  `NULL` in `WHERE effective_from <= x AND effective_to > x` lookups.
- **DELETE closes the row in Type-2 without inserting a tombstone**.
  The `current_by_natural` cache drops the entry; the last row's
  `is_current` flips to False. Reports that filter `WHERE is_current`
  correctly omit deleted entities without needing a `tombstone`
  column.
- **Type 6 reads `previous_attributes` from `change.before`**, not
  from the prior in-state row. That makes the applier stateless WRT
  attribute history beyond "one update at a time".
- **JSONL throughout**, no Parquet / Avro dependency. Production
  callers swap the codec for whatever format their DW ingests.

## Quality

```bash
make test       # 77 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **77 tests**, 0 failing; 6 Hypothesis properties (detect is well-formed
  for arbitrary snapshot pairs, INSERT/DELETE key sets are disjoint,
  Type-1 is idempotent on no-op, Type-2 current view matches the after
  snapshot, Type-2 history row count ≥ INSERTs + UPDATEs, `detect(s, s)`
  is empty).
- mypy `--strict` clean over 7 source files; ruff clean.
- Multi-stage slim Docker image, non-root `scdkit` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
