# Changelog

## 0.1.0

Initial release.

* `Record(key, seq, value, tombstone)` frozen dataclass.
* `merge_runs(runs, keep_tombstones=False)` — streaming k-way merge
  with last-write-wins and tombstone consumption.
* `simulator.generate_runs` — deterministic overlapping sorted-run
  generator.
* `lsmmerge` CLI: `info | simulate | merge`.
* JSONL codec for `Record`.
* Hypothesis property tests covering sortedness, uniqueness,
  last-write-wins, and tombstone consumption.
