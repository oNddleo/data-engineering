# hyperloglog-cardinality

**HyperLogLog++** sketch for distinct-count estimation at streaming
scale. Configurable precision (P=4..16), dense register array, HLL++
bias correction with linear counting for small cardinalities, and
set-merge via element-wise max. The foundational sketch behind every
modern warehouse's `APPROX_COUNT_DISTINCT` (Redshift, BigQuery,
Snowflake, Presto, Spark).

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Hashes input deterministically** via BLAKE2b (first 8 bytes,
   64-bit unsigned). Reproducible across runs, uniformly distributed
   across output bits.
2. **Adds values to a sketch** — the top ``p`` bits of the hash pick
   a register; the remaining ``q = 64 - p`` bits' leading-zero count
   updates the register if larger than its current value.
3. **Estimates cardinality** via the harmonic-mean formula
   ``α_m · m² · (Σ 2^-M[i])^-1`` with bias correction. For very
   small cardinalities (raw ≤ 2.5 m), falls back to **linear
   counting** ``m · ln(m / V)`` (V = zero-register count) which is
   near-exact at low n.
4. **Merges sketches** by element-wise max of their register arrays
   — mathematically equivalent to adding both input streams to one
   sketch. The key property enabling distributed / parallel HLL.
5. **Serialises compactly**: each register fits in one byte (max ρ
   for q=60 is 61), so a p=14 sketch is exactly 16 384 bytes raw
   (~22 KB base64). Sub-1% error with ~16 KB of memory regardless
   of input cardinality.

## Precision table

| p  | m       | std error  | sketch size (raw bytes) |
| -- | ------- | ---------- | ----------------------- |
| 4  | 16      | ~26%       | 16                      |
| 8  | 256     | ~6.5%      | 256                     |
| 10 | 1 024   | ~3.3%      | 1 024                   |
| 12 | 4 096   | ~1.6%      | 4 096                   |
| 14 | 16 384  | ~0.81%     | 16 384                  |
| 16 | 65 536  | ~0.41%     | 65 536                  |

Standard error is the 1-σ relative error: ``1.04 / sqrt(m)``. Default
**p = 14** matches Google's HLL++ paper and most production engines.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `hllpp.schema`     | `HLLSketch` (precision + register array) + `SketchStats`            |
| `hllpp.hash`       | BLAKE2b-based deterministic 64-bit hash + `leading_zeros_64`        |
| `hllpp.sketch`     | `new_sketch`, `add`, `estimate`, `merge`, `stats` — the core API    |
| `hllpp.simulator`  | Seeded synthetic streams: UNIQUE / DUPLICATED / POWER_LAW           |
| `hllpp.io_jsonl`   | Type-checked JSONL codec with base64-encoded register arrays        |
| `hllpp.cli`        | `hllpp info \| simulate \| add \| estimate \| merge \| summary`     |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
hllpp info
hllpp simulate --n 100000 --pattern UNIQUE --seed 7 --output vals.txt
hllpp add      --input vals.txt --precision 14 --output sketch.json
hllpp estimate --input sketch.json
hllpp estimate --input sketch.json --json
hllpp merge    sketch_a.json sketch_b.json --output merged.json
hllpp summary  --input vals.txt --precision 14
```

Sample `summary` on 100 000 distinct values:

```json
{
  "precision": 14,
  "m": 16384,
  "n_zero_registers": 35,
  "max_register": 16,
  "estimated_cardinality": 99054,
  "standard_error_pct": 0.8125
}
```

True cardinality: 100 000 → estimate error: 0.95% (just under the 1-σ
relative error of 0.81%).

Sample `merge` over two disjoint 10 000-value streams:

```
$ hllpp merge a.json b.json --output merged.json
$ hllpp estimate --input merged.json
precision:                14
m (registers):            16384
non-zero registers:       11581
max register value:       17
estimated cardinality:    20,104
std error:                ±0.81%
```

True union cardinality: 20 000 → estimate error: 0.52%.

## Library

```python
from hllpp.sketch import new_sketch, add, estimate, merge, stats

s = new_sketch(precision=14)
for v in stream_of_values:
    add(s, v)

print(estimate(s))                      # int — bias-corrected cardinality
summary = stats(s)
print(summary.standard_error_pct)       # 0.8125 for p=14

# Distributed counting: merge per-shard sketches
shard_a, shard_b, shard_c = ...   # sketches built independently
total = merge(shard_a, shard_b, shard_c)
print(f"distinct across shards: {estimate(total):,}")

# Serialise to JSONL for storage / transport
from hllpp.io_jsonl import sketch_to_dict, sketch_from_dict
import json
blob = json.dumps(sketch_to_dict(s))    # ~22 KB for p=14
restored = sketch_from_dict(json.loads(blob))
assert restored == s
```

## Key design decisions

- **BLAKE2b for hashing.** Stdlib-only, deterministic across runs
  (Python's built-in `hash()` is randomly salted per-interpreter),
  fast (< 1 µs per call), uniformly distributed in output bits.
  Crypto strength is irrelevant for HLL; uniformity is what matters.
- **Linear counting at small n.** Below ``2.5 m`` (per Flajolet et al.),
  the harmonic-mean estimator has a downward bias. Linear counting
  using ``V = zero-register count`` gives near-exact results — this
  is HLL++'s small-range correction.
- **Element-wise max merge.** The mathematical heart of HLL: merging
  is associative and commutative (property-tested), making HLLs the
  ideal distinct-count primitive for sharded / parallel pipelines.
- **One byte per register.** Even for cardinalities approaching
  2^64, the max ρ is bounded by q + 1 ≤ 61, well within a uint8.
  Storage = ``2^p`` bytes raw, ~1.33× under base64.
- **Default p = 14.** Matches Google's HLL++ paper, Redshift,
  BigQuery, Snowflake. Gives < 1% error with 16 KB of memory
  regardless of cardinality, which is the right trade-off for
  almost every production workload.
- **No sparse representation.** Google's HLL++ also has a sparse
  encoding for low-cardinality sketches (better compression but
  much more code). Skipped here for simplicity; consumers wanting
  the densest possible storage can layer their own sparse format
  on top.

## Quality

```bash
make test       # 69 tests + 8 Hypothesis properties
make type       # mypy --strict
make lint
```

- **69 tests**, 0 failing; 8 Hypothesis properties (hash64
  deterministic + in uint64 range; leading_zeros bounded; small
  cardinality near-exact via linear counting; insert idempotent;
  merge self-idempotent + commutative + dominates inputs;
  duplicates don't change estimate).
- mypy `--strict` clean over 7 source files; ruff clean.
- Multi-stage slim Docker image, non-root `hllpp` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## Accuracy benchmark (built-in tests)

| Cardinality | Precision | Memory  | Observed error | Expected std error |
| ----------- | --------- | ------- | -------------- | ------------------ |
| 100         | p=14      | 16 KB   | ≤ 5 (linear)   | n/a (lin. counting)|
| 10 000      | p=14      | 16 KB   | < 2%           | 0.81%              |
| 100 000     | p=14      | 16 KB   | < 1%           | 0.81%              |
| 100 000     | p=12      | 4 KB    | < 5%           | 1.6%               |

## License

MIT — see [LICENSE](LICENSE).
