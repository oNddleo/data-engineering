# Changelog

## [0.1.0] — 2026-05-18

### Added
- `HLLSketch` frozen-slots dataclass with `precision`
  (4 ≤ p ≤ 16, default 14) and `registers: list[int]`.
  Auto-fills register array to ``2^precision`` zeros at construction.
- `SketchStats` snapshot with `precision`, `m`, `n_zero_registers`,
  `max_register`, `estimated_cardinality`, and computed
  `standard_error_pct = 1.04 / sqrt(m) * 100`.
- Precision constants: `MIN_PRECISION = 4`, `MAX_PRECISION = 16`,
  `DEFAULT_PRECISION = 14`.
- `hllpp.hash`:
  - `hash64()` — deterministic 64-bit unsigned hash via BLAKE2b's
    first 8 bytes. Handles str, bytes, int, float input.
  - `leading_zeros_64()` — count of leading zeros (1-indexed
    first-1 position) for a q-bit field.
- `hllpp.sketch`:
  - `new_sketch(precision)` — fresh empty sketch.
  - `add(sketch, value)` — hash, dispatch to register, update
    if leading-zeros count > current.
  - `estimate(sketch)` — bias-corrected harmonic mean estimator
    with **linear counting** for raw ≤ 2.5 m.
  - `merge(*sketches)` — element-wise max of register arrays.
    Requires matching precision.
  - `stats(sketch)` — `SketchStats` snapshot.
- `hllpp.simulator.generate()` — seeded streams across three
  patterns: UNIQUE (every value distinct), DUPLICATED (n // k
  distinct values × k repetitions), POWER_LAW (Zipf with
  configurable skew). Values are seed-namespaced so disjoint
  seeds yield disjoint sets.
- `hllpp.io_jsonl` — type-checked JSONL codec. Register arrays
  stored as **base64-encoded bytes** (one byte per register, since
  max ρ ≤ 61). Rejects type confusions on load.
- `hllpp.cli` — `hllpp info | simulate | add | estimate | merge |
  summary`.
- 69 unit tests + 8 Hypothesis properties; mypy `--strict` clean
  over 7 source files; ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/hyperloglog-cardinality-v0.1.0
