# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — frozen `Reservoir` snapshot + mutable
  `BuildableReservoir` (shared by Algorithm R and L), `WeightedItem`
  (mean + weight + priority key), `WeightedReservoir` for A-Res.
* **Algorithm R** (Vitter 1985) — textbook O(N) reservoir sampler;
  every stream item has exact k/N probability of ending in the sample.
* **Algorithm L** (Li 1994) — O(k · (1 + log(N/k))) geometric-jump
  variant; uses ``W = u^(1/k)`` to skip past items that wouldn't
  change the reservoir.
* **A-Res weighted** (Efraimidis & Spirakis 2006) — per-item priority
  key ``key = u^(1/w_i)``; reservoir maintains top-k by key
  ascending so the smallest-key slot is the cheap-to-evict head.
* **Merge** — ``merge_uniform`` recombines two uniform reservoirs
  (weighted by each side's ``n_seen``); ``merge_weighted`` is exactly
  mergeable (union of priority keys → top-k).
* **Simulator** — uniform / Zipf streams + weighted pairs with
  uniform / power / binary weight distributions for benchmarking.
* **CLI** — `info | sample | merge | bench`; the `bench` command
  empirically verifies the uniformity guarantee by running many
  trials and reporting per-item pick counts.
* **JSONL codec** — round-trip for both reservoir shapes; sortedness
  + capacity invariants enforced on decode.
* **Quality gate** — 89 tests with Hypothesis property tests
  (n_seen / subset / sortedness / round-trip / merge conservation);
  empirical uniformity check on both R and L; ``mypy --strict``
  clean; ruff lint + format clean; zero runtime deps.
