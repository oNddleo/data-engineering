# Changelog

## 0.1.0

Initial release.

* `Species` / `Market` / `Grade` / `Form` enums covering VN seafood
  exports.
* `ExportRecord` frozen-slots dataclass with derived
  `fob_value_usd_cents`.
* `benchmark_usd_cents_per_kg(species, market, grade)` — illustrative
  reference FOB table.
* `is_dumping_risk(...)` predicate (default 25 % below benchmark).
* `aggregate_by_species` / `aggregate_by_market` /
  `aggregate_by_species_market` / `aggregate_by_exporter` rollups.
* `simulator.generate` — deterministic synthetic export records.
* `vnfishery` CLI: `info | benchmark | dumping-watch | aggregate
  | simulate`.
* JSONL codec for `ExportRecord`.
* Hypothesis property tests for aggregate-totals-match-input and
  dumping-risk-vs-benchmark.
