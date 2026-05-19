# bloom-filter

Production-grade **Bloom-filter toolkit** in pure Python 3.10+ —
classic, counting, and scalable variants with optimal-size helpers,
set operations (union, intersection estimate), and JSONL persistence.

Companion to [`hyperloglog-cardinality`](../hyperloglog-cardinality)
(distinct counts) and [`count-min-sketch`](../count-min-sketch)
(frequency estimation). Together they cover the three classic
probabilistic-data-structure questions in streaming pipelines.

Zero runtime dependencies (stdlib only), `mypy --strict` clean,
98 tests including Hypothesis property tests.

## What's in the box

| Module                 | Purpose                                          |
| ---------------------- | ------------------------------------------------ |
| `bloom.schema`         | `BloomFilter` (frozen), `BuildableBloom`, `CountingBloom`, `ScalableBloom` |
| `bloom.hash`           | BLAKE2b multi-seed hash family (deterministic)   |
| `bloom.sizing`         | Optimal `m`, `k`, FPR estimation                 |
| `bloom.filter`         | `build`, `add`, `contains`, `union`, `intersect_estimate`, `freeze`, `thaw` |
| `bloom.counting`       | `build_counting`, `add_counting`, `remove_counting` |
| `bloom.scalable`       | Almeida 2007 dynamic-growth variant              |
| `bloom.simulator`      | `uniform_stream`, `zipf_stream`, `mixed_stream`  |
| `bloom.io_jsonl`       | JSONL codec for every variant                    |
| `bloom.cli`            | `info | size | build | check | bench`           |

## Quick start

```bash
# How big does a Bloom filter for 1M items at 1% FPR need to be?
python -m bloom.cli size --capacity 1000000 --fpr 0.01
# → size_bits: 9 585 059, n_hashes: 7, bytes: 1.2 MB

# Build a filter from a value file
python -m bloom.cli build --input values.txt --fpr 0.01 \
  --output filter.jsonl

# Check membership of a batch of queries
python -m bloom.cli check --filter filter.jsonl --input queries.txt

# Synthetic FPR benchmark
python -m bloom.cli bench --n-positive 10000 --n-negative 50000 --fpr 0.01
```

```python
from bloom import build, add, contains, freeze, union

bf = build(capacity=1_000_000, target_fpr=0.01)
for url in stream_of_seen_urls():
    add(bf, url)

if contains(bf, "https://example.com/maybe"):
    # False positive rate ≤ 1% — verify against source-of-truth.
    pass

snapshot = freeze(bf)
# snapshot is hashable, picklable, JSON-serializable.

other = freeze(build_from_other_node())
merged = union(snapshot, other)   # exact bitwise union
```

## Variants

| Variant         | Mutable? | Memory   | Deletion?       | Growth?  |
| --------------- | -------- | -------- | --------------- | -------- |
| `BloomFilter`   | no       | 1 bit/cell | no            | no       |
| `BuildableBloom`| yes      | 1 bit/cell | no            | no       |
| `CountingBloom` | yes      | 1 byte/cell | yes          | no       |
| `ScalableBloom` | yes      | 1 bit/cell | no            | yes      |

## Sizing math

Given `n` items and target FPR `p`:

* **bits** `m = ⌈ -n · ln(p) / (ln 2)² ⌉`   (≈ 9.585 bits/item at 1%)
* **hashes** `k = round((m/n) · ln 2)`   (≈ 7 at 1%)
* **observed FPR** `(1 − e^(−kn/m))^k`

The `bloom.sizing` module exposes all four formulas plus a
`bits_per_item(p)` convenience.

## Hash family

We derive `k` independent hashes from a single primitive (BLAKE2b)
by varying the 16-byte `person` parameter — same pattern as our
Count-Min-Sketch package. Deterministic across processes (no random
PYTHONHASHSEED issues), no external deps, ~250 ns per hash.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 10 source files clean
pytest                        # 98 tests, all green
```

## License

MIT
