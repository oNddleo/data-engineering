# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — `CDCEvent` (Debezium-style envelope) with four `Op`
  values (c/u/d/r), `EventPosition` (log_file + offset for total
  ordering), `ChangeVector` (column-level UPDATE diff),
  `RowLineage` (per-row history). Strict per-op invariants enforced
  on construction (e.g. CREATE must have empty before + non-empty
  after).
* **Replay** — `apply_event(snapshot, event)` and bulk `replay` /
  `replay_unordered` with `strict` / lenient modes. Out-of-order
  events are rejected (strict) or dropped (lenient).
* **Compaction** — `compact(events)` collapses each PK's lifecycle
  to the latest surviving event. `compact_to_inserts` additionally
  rewrites UPDATE → INSERT for clean target-table materialisation.
  Orphan DELETEs are dropped silently.
* **Diff** — `change_vector(event)` returns the column subset that
  actually changed in an UPDATE. `is_no_op_update` catches
  trigger-induced touches. `columns_changed` convenience helper.
* **Lineage** — `build_lineage(events)` produces one `RowLineage`
  per `(table, pk)` carrying `created_at_ms`, `last_modified_at_ms`,
  `n_updates`, and `is_deleted`. Monotonic timestamp semantics
  (out-of-order ts_ms doesn't push `last_modified_at_ms` backward).
* **Simulator** — `generate` produces a realistic ``customers`` +
  ``orders`` workload with configurable delete fraction and seeded
  randomness.
* **CLI** — `info | simulate | replay | compact | diff | lineage`.
* **JSONL codec** — round-trip for `CDCEvent`, `ChangeVector`,
  `RowLineage`. Strict JSON-scalar typing on column values
  (`str | int | float | bool | None`).
* **Quality gate** — 119 tests with Hypothesis property tests
  (replay/compact equivalence, replay-unordered order-invariance,
  compaction idempotence, JSONL round-trip, lineage column subset);
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
