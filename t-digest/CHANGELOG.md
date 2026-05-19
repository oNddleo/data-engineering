# Changelog

## 0.1.0 — 2026-05-19

Initial production-grade release.

* **Schema** — frozen `Centroid` (mean + weight) and `TDigest`
  (sorted centroids + total_weight + min/max pinning), mutable
  `BuildableTDigest` with append-only buffer.
* **Scale function** — Dunning's k1 (`k(q) = δ/(2π) · arcsin(2q − 1)`)
  + `max_combined_weight` size bound + analytic inverse `q_from_k`.
* **Core ops** — buffer-then-merge variant: O(1) `add`, periodic
  `compress` that sorts and greedily merges adjacent centroids;
  linear-interpolation `quantile` / `cdf` with exact min/max pinning;
  exact `merge` for distributed aggregation; `freeze` / `thaw` for
  snapshot ↔ buildable conversions.
* **Simulator** — `uniform_stream`, `gaussian_stream`,
  `lognormal_stream`, `pareto_stream` + `exact_quantile` baseline
  for accuracy validation.
* **CLI** — `info | build | quantile | cdf | bench` with JSON output;
  `bench` reports per-quantile relative error against the exact
  baseline.
* **JSONL codec** — round-trip for `TDigest` snapshots with float-list
  centroid encoding.
* **Quality gate** — 80 tests with Hypothesis property tests
  (monotonicity, weight conservation, k-inverse round-trip);
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.

Empirical accuracy at compression=100 on 100k samples: ~60 centroids,
p99 within 2%, p999 within 8% on lognormal.
