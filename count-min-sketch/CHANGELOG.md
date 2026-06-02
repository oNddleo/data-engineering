# Changelog

## [0.1.0] — 2026-05-19

### Added
- `SketchConfig` frozen-slots dataclass with `epsilon` (relative
  error bound) and `delta` (failure probability). Computed
  properties: `width = ⌈e/ε⌉` and `depth = ⌈ln(1/δ)⌉`.
- `CountMinSketch` frozen-slots dataclass holding the ``d × w``
  counter table + ``total_count``. Auto-fills register array on
  construction; validates row/column shape on explicit `rows=...`.
- `HeavyHitter` (value + estimated_count + fraction_of_total) and
  `SketchStats` (width, depth, n_cells, total, max, ε·N error bound).
- `MAX_COUNT = 2^32 - 1` — counters saturate to prevent wrap-around.
- `cms.hash` — BLAKE2b-derived family with per-row `person` seeds:
  - `hash64(value, seed)` — deterministic 64-bit hash.
  - `index_for(value, seed, width)` — bucket index in `[0, width)`.
- `cms.sketch`:
  - `new_sketch(config)` — fresh empty sketch.
  - `update(sketch, value, count=1)` — increment d cells; returns
    new sketch (immutable). Rejects negative count; zero is a noop.
  - `estimate(sketch, value)` — return min of d cells (one-sided
    over-estimate).
  - `merge(*sketches)` — element-wise sum. Validates matching config.
  - `stats(sketch)` — `SketchStats` snapshot.
- `cms.heavy`:
  - `top_k_two_pass(sketch, values, k)` — two-pass extraction
    over a pre-built sketch + the raw input.
  - `HeavyHittersBuilder` — online Misra-Gries candidate-set +
    CMS for single-pass top-K with bounded memory (`k + buffer`
    candidates).
  - `exact_heavy_hitters(values, k)` — reference implementation
    via in-memory counting.
- `cms.simulator.generate()` — seeded streams across UNIFORM /
  ZIPF / HEAVY_HITTERS patterns. Values are seed-namespaced
  (`s<seed>_v_<i>`) so disjoint seeds yield disjoint vocabularies.
- `cms.io_jsonl` — type-checked JSONL codec. Counter rows
  base64-encoded as 4-byte big-endian uints for compact storage.
- `cms.cli` — `cms info | simulate | add | estimate | merge |
  heavy | summary`.
- 84 unit tests + 8 Hypothesis properties; mypy `--strict` clean
  over 8 source files; ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/count-min-sketch-v0.1.0
