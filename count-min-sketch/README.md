# count-min-sketch

**Count-Min sketch** (Cormode & Muthukrishnan 2003) for frequency
estimation at streaming scale. Configurable ε / δ trade-off, one-sided
bounded over-estimation, set-merge via element-wise sum, and top-K
**heavy-hitters** extraction (two-pass or online Misra-Gries +
CMS). Pairs with [`hyperloglog-cardinality`](../hyperloglog-cardinality)
(#46) as the "frequency" half of the linear-sketch family — the two
together cover the foundational use cases in every modern warehouse.

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Maintains a ``d × w`` table of 32-bit counters** where:
   - ``w = ⌈e / ε⌉`` — column count, controls per-bucket collision rate.
   - ``d = ⌈ln(1/δ)⌉`` — row count, controls failure probability.
2. **Updates each row independently** via a seeded BLAKE2b hash
   family (one row per seed). Increment hits ``d`` cells per insert.
3. **Estimates a value's count** by returning the **minimum** of
   its ``d`` cells — every cell is an over-estimate; the min is
   the tightest. Guarantee (with probability ≥ 1 − δ):

   ```
   true_count ≤ estimate ≤ true_count + ε · total_count
   ```

4. **Merges two sketches** by element-wise sum of their counter
   tables — mathematically equivalent to feeding both streams to
   one sketch. The basis for distributed counting.
5. **Extracts top-K heavy hitters** via either:
   - **Two-pass**: build CMS from the stream, then walk distinct
     values and rank by CMS estimate.
   - **Online**: `HeavyHittersBuilder` runs CMS + a bounded
     Misra-Gries candidate set in parallel for one-pass operation.

## Precision table

| ε        | δ      | width w | depth d | memory  |
| -------- | ------ | ------- | ------- | ------- |
| 0.01     | 0.01   | 272     | 5       | 5.3 KB  |
| 0.001    | 0.01   | 2 719   | 5       | 53 KB   |
| **0.001**| **0.001** | **2 719** | **7** | **74 KB** *(default)* |
| 0.0001   | 0.001  | 27 183  | 7       | 740 KB  |

(Each cell is a 32-bit unsigned counter.)

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `cms.schema`       | `CountMinSketch`, `SketchConfig`, `SketchStats`, `HeavyHitter`      |
| `cms.hash`         | BLAKE2b-based hash family with `personalization` seeds              |
| `cms.sketch`       | `new_sketch`, `update`, `estimate`, `merge`, `stats`                |
| `cms.heavy`        | `top_k_two_pass`, `HeavyHittersBuilder`, `exact_heavy_hitters`      |
| `cms.simulator`    | Seeded streams: UNIFORM / ZIPF / HEAVY_HITTERS                      |
| `cms.io_jsonl`     | Type-checked JSONL codec (base64-encoded counter rows)              |
| `cms.cli`          | `cms info \| simulate \| add \| estimate \| merge \| heavy \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
cms info
cms simulate --n 50000 --vocab 100 --pattern ZIPF --skew 1.5 --seed 7 --output vals.txt
cms add      --input vals.txt --epsilon 0.001 --delta 0.001 --output sketch.json
cms estimate --input sketch.json --value "s7_v_00000000"
cms heavy    --input vals.txt --k 5
cms merge    sketch_a.json sketch_b.json --output merged.json
cms summary  --input vals.txt
```

Sample `heavy` over a Zipf-skewed stream:

```
rank value                                 count  frac%
   1 s7_v_00000000                        20,824  41.6%
   2 s7_v_00000001                         7,309  14.6%
   3 s7_v_00000002                         3,991   8.0%
   4 s7_v_00000003                         2,594   5.2%
   5 s7_v_00000004                         1,906   3.8%
```

Sample `summary` after 50 000 inserts at ε=0.001 / δ=0.001:

```json
{
  "width": 2719,
  "depth": 7,
  "n_cells": 19033,
  "total_count": 50000,
  "max_counter": 20824,
  "epsilon": 0.001,
  "delta": 0.001,
  "standard_error_bound": 50
}
```

Sample `merge` over two disjoint 10 000-value uniform streams (vocab 50 each):

```
$ cms estimate --input merged.json --value "s1_v_00000000"
value:               s1_v_00000000
estimated count:     185
total stream count:  20,000
error bound (ε·N):  20
```

True count: 200 (uniform over 50 values × 10 000) — estimate 185
within the 20-unit bound. ✓

## Library

```python
from cms.heavy   import HeavyHittersBuilder, top_k_two_pass
from cms.schema  import SketchConfig
from cms.sketch  import new_sketch, update, estimate, merge, stats

# Single-stream usage
s = new_sketch(SketchConfig(epsilon=0.001, delta=0.001))
for v in stream_of_values:
    s = update(s, v)
print(estimate(s, "some_key"))    # int — over-estimate within ε·N

# Top-K heavy hitters (two-pass)
hh = top_k_two_pass(s, stream_of_values, k=10)
for h in hh:
    print(h.value, h.estimated_count, h.fraction_of_total)

# Online: Misra-Gries + CMS in one pass
b = HeavyHittersBuilder(sketch=new_sketch(), k=10, buffer=50)
for v in stream:
    b.add(v)
print(b.top_k())

# Distributed counting: merge per-shard sketches
total = merge(shard_a, shard_b, shard_c)
print(estimate(total, "globally_hot_key"))
```

## Key design decisions

- **BLAKE2b ``personalization`` for seeds.** A clean way to derive
  ``d`` independent deterministic hash functions from one library
  call. Each seed produces a different ``person`` byte string, so
  the underlying state differs from row to row.
- **One-sided over-estimation only.** The min-trick (return the
  minimum of the d row-estimates) guarantees the result is ≥ true.
  Over-estimation never exceeds ``ε · total_count`` with probability
  ≥ 1 − δ.
- **32-bit counters with saturation.** Counters cap at ``2^32 − 1``
  (≈ 4.3 B). Saturating add prevents wrap-around on extreme inputs.
- **Merge is element-wise sum** (not max, unlike HLL). Adding two
  same-config sketches gives a sketch equivalent to feeding both
  streams to one — provable: every increment lands in the same d
  cells regardless of which sketch absorbed it.
- **Two paths for heavy-hitters.** Two-pass is cleanest when the
  stream fits in memory or can be re-read. Online via Misra-Gries
  + CMS is single-pass, bounded memory, but only correct for
  values with frequency > ``total / (k + buffer)``.
- **Pure stdlib.** `hashlib` + `dataclasses` + `enum` + `json`. The
  base64 register encoding keeps storage compact (~76 KB for the
  default precision) while staying language-agnostic.

## Quality

```bash
make test       # 84 tests + 8 Hypothesis properties
make type       # mypy --strict
make lint
```

- **84 tests**, 0 failing; 8 Hypothesis properties (hash deterministic
  + index in range; estimate ≥ true count; estimate ≤ total count;
  merge(s, s).rows == 2× s.rows; merge commutative; total_count ==
  insert count; CMS top-1 agrees with exact-counting on dominant
  values).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `cms` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
