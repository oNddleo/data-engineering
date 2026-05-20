# change-data-capture

Production-grade **CDC (change-data-capture) toolkit** in pure
Python 3.10+ — Debezium-style event envelopes, snapshot replay,
log compaction, column-level diff, and per-row lineage.

The five primitives every modern streaming-CDC system (Debezium,
Maxwell, Airbyte CDC, ksqlDB CDC, ...) needs to build on top of —
without dragging in any of those frameworks. Zero runtime
dependencies, `mypy --strict` clean, 119 tests including Hypothesis
property tests.

## What's in the box

| Module             | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `cdc.schema`       | `CDCEvent` envelope, `Op` enum, `EventPosition`, `ChangeVector`, `RowLineage` |
| `cdc.replay`       | `apply_event` / `replay` / `replay_unordered` — materialize a snapshot |
| `cdc.compact`      | `compact` / `compact_to_inserts` — keep only the latest event per PK |
| `cdc.diff`         | `change_vector` / `columns_changed` / `is_no_op_update` |
| `cdc.lineage`      | `build_lineage` — per-row creation + modification history |
| `cdc.simulator`    | `generate(n_customers, n_orders, seed)` — synthetic event stream |
| `cdc.io_jsonl`     | JSONL codec for every record type                  |
| `cdc.cli`          | `info | simulate | replay | compact | diff | lineage` |

## Event envelope

Every CDC event carries the canonical Debezium-flavoured fields:

```json
{
  "op": "u",
  "table": "orders",
  "pk": "42",
  "ts_ms": 1715251200000,
  "position": {"log_file": "binlog.000123", "offset": 4567},
  "before": {"id": 42, "status": "pending", "total_vnd": 100000},
  "after":  {"id": 42, "status": "paid",    "total_vnd": 100000},
  "db": "shop"
}
```

Four ``op`` values:

| Op | Meaning  | `before` | `after`  |
| -- | -------- | -------- | -------- |
| c  | INSERT   | empty    | row      |
| u  | UPDATE   | prev row | new row  |
| d  | DELETE   | prev row | empty    |
| r  | READ (initial snapshot) | empty | row |

## Quick start

```bash
# Generate a synthetic event stream
python -m cdc.cli simulate --customers 30 --orders 100 --seed 11 \
  --output events.jsonl

# Materialize the current snapshot (in-strict-order or unordered)
python -m cdc.cli replay --input events.jsonl --show 5

# Compact to the minimum event set per PK (Kafka-style log compaction)
python -m cdc.cli compact --input events.jsonl --output compacted.jsonl

# Column-level diff for every UPDATE
python -m cdc.cli diff --input events.jsonl --output diffs.jsonl

# Per-row lineage (created_at, n_updates, is_deleted)
python -m cdc.cli lineage --input events.jsonl --show 5
```

```python
from cdc import (
    CDCEvent, EventPosition, Op,
    replay, compact, change_vector, build_lineage,
)

events = [
    CDCEvent(op=Op.CREATE, table="users", pk="1", ts_ms=1_000,
             position=EventPosition("binlog.000001", 1),
             after={"id": 1, "name": "Alice", "age": 30}),
    CDCEvent(op=Op.UPDATE, table="users", pk="1", ts_ms=2_000,
             position=EventPosition("binlog.000001", 2),
             before={"id": 1, "name": "Alice", "age": 30},
             after={"id": 1, "name": "Alice", "age": 31}),
]

# Materialize the current state.
snap = replay(events)
# {('users', '1'): {'id': 1, 'name': 'Alice', 'age': 31}}

# Compact (collapses to a single UPDATE).
compacted = compact(events)

# Column-level diff for an UPDATE.
diff = change_vector(events[1])
# ChangeVector(changed_columns=('age',))

# Build per-row lineage.
lineage = build_lineage(events)
# [RowLineage(table='users', pk='1', created_at_ms=1000,
#             last_modified_at_ms=2000, n_updates=1, is_deleted=False)]
```

## Out-of-order tolerance

CDC streams from multi-partition sources don't always arrive in
position order. We expose two modes on every replay path:

* **strict** (default) — raises ``ValueError`` on stale or
  illegal-transition events. Use for golden-source pipelines where
  any out-of-order event is a real bug.
* **lenient** (``strict=False``) — silently drops late events and
  treats orphan UPDATE/DELETE as INSERT/no-op. Use for forgiving
  ingest pipelines that tolerate replays + duplicates.

``replay_unordered(events)`` sorts by position first, then replays.

## Compaction

Kafka-log-style compaction reduces an event stream to **one event
per primary key** — the one that fully captures the row's end state:

* INSERT → UPDATE → ... → UPDATE collapses to one UPDATE.
* INSERT → UPDATE → DELETE collapses to one DELETE.
* INSERT → DELETE → INSERT (recreation) collapses to one INSERT.
* Orphan DELETE (DELETE without prior CREATE/UPDATE in the input)
  is dropped silently.

``compact_to_inserts`` is the same but rewrites every surviving
UPDATE to an INSERT — useful when materializing a fresh target table.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 9 source files clean
pytest                        # 119 tests, all green
```

Property tests verify: replay/compact equivalence, replay-unordered
order-independence (any permutation produces the same snapshot),
compaction idempotence (compact ∘ compact = compact), JSONL
round-trip, and lineage column subset.

## License

MIT
