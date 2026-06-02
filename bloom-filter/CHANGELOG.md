# Changelog

## 0.1.0 — 2026-05-19

Initial production-grade release.

* **Schema** — four data shapes: `BloomFilter` (frozen, int-backed
  bit-array), `BuildableBloom` (mutable, bytearray-backed),
  `CountingBloom` (saturating byte counters, supports deletion),
  `ScalableBloom` (chained slices, dynamic growth).
* **Hash family** — BLAKE2b with personalization byte per seed →
  deterministic, independent multi-seed hashing without external deps.
* **Sizing helpers** — `optimal_size_bits`, `optimal_n_hashes`,
  `estimate_fpr`, `estimate_fpr_from_fill`, `bits_per_item` (all
  derived from the textbook Bloom-1970 formulas).
* **Set operations** — exact `union` (bitwise OR); approximate
  `intersect_estimate` (bitwise AND).
* **Counting variant** — `add_counting` / `remove_counting` with
  saturation at 255; refuses to decrement a counter at zero (preserves
  no-false-negative guarantee).
* **Scalable variant** — Almeida-2007 chained-slice growth with
  configurable `growth_factor` (default 2) and `tightening_ratio`
  (default 0.5); `cumulative_fpr_bound` reports the geometric-series
  upper bound.
* **Simulator** — `uniform_stream`, `zipf_stream`, `mixed_stream`
  (disjoint positives / negatives for empirical FPR measurement).
* **CLI** — `info | size | build | check | bench` with JSON output.
* **JSONL codec** — hex-encoded bit arrays for snapshots, base64 for
  large bytearray payloads.
* **Quality gate** — 98 tests with Hypothesis property tests;
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
