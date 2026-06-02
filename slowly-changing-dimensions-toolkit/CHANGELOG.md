# Changelog

## [0.1.0] — 2026-05-17

### Added
- `SCDType` enum covering the five Kimball types implemented in this
  toolkit (`TYPE_1`, `TYPE_2`, `TYPE_3`, `TYPE_4`, `TYPE_6`).
- `ChangeKind` enum (`INSERT` / `UPDATE` / `DELETE`).
- `DimensionRow`, `DimensionChange` frozen-slots dataclasses with
  validation at construction (tz-aware datetimes, non-empty natural
  keys, INSERT-without-before / DELETE-without-after invariants,
  UPDATE-must-list-changed-attrs).
- `HIGH_DATE = 9999-12-31 23:59:59 +07:00` sentinel for open-ended
  `effective_to` on the current Type-2 row.
- `detect(before, after, as_of, tracked_attrs?) → list[DimensionChange]`
  — pure-function snapshot diff. Untracked-attribute changes silently
  skipped to prevent runaway Type-2 history from a `last_load_ts`
  bump. Output sorted by `(kind, natural_key)` for stable diffs.
- Five appliers — `apply_type_1` (overwrite),
  `apply_type_2` (new row per change),
  `apply_type_3` (previous-value column),
  `apply_type_4` (separate history table),
  `apply_type_6` (hybrid 1+2+3). Each a pure function that doesn't
  mutate its input.
- `Type2State` / `Type4State` / `Type6State` immutable state containers
  with monotonic-integer surrogate-key assignment; `start_surrogate`
  parameter lets chained batches stay collision-free.
- `type_2_current(state)` returns the as-of-now view;
  `type_2_history_for(state, natural_key)` returns one entity's
  version chain sorted by `effective_from`.
- DELETE in Type-2 closes the current row (`is_current=False`,
  `effective_to=detected_at`) without inserting a tombstone — reports
  filtering `WHERE is_current` correctly omit deleted entities.
- Seeded synthetic generator producing realistic Shopee-seller
  snapshots with configurable insert/update/delete fractions.
- Type-checked JSONL codec for snapshots, change events, and
  dimension rows.
- CLI `scdkit info | simulate | detect | apply | history | summary`.
- 77 tests + 6 Hypothesis properties (detect is well-formed for
  arbitrary snapshots; INSERT/DELETE key sets are disjoint; Type-1
  is idempotent on a no-op diff; Type-2 current view matches the
  after snapshot; Type-2 history row count ≥ INSERTs+UPDATEs;
  `detect(s, s)` is empty).
- mypy `--strict` clean over 7 source files; ruff clean.
- Multi-stage slim Docker image, non-root `scdkit` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- An earlier draft of `apply_type_6` looked up the previous value
  from the prior in-state row, requiring two state lookups per
  UPDATE. The released version reads `previous_attributes` from
  `change.before` instead — simpler, faster, and the same answer
  whenever the caller built the change via `detect` (which always
  fills `before`).
- The Hypothesis property `test_type_2_current_matches_after_snapshot`
  catches the most common Type-2 bug: a missing close-out on
  UPDATE that leaves two `is_current=True` rows for the same
  natural key.
