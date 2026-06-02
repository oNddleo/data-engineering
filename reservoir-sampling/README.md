# reservoir-sampling

Production-grade **streaming reservoir-sampling toolkit** in pure
Python 3.10+ — three canonical algorithms (Vitter R, Li L, and
Efraimidis–Spirakis A-Res for weighted streams) plus a distributed-
shard merge primitive.

Zero runtime dependencies (stdlib only), `mypy --strict` clean,
89 tests including Hypothesis property tests and a uniformity-bench
that empirically verifies the k/N guarantee across thousands of
trials.

## What's in the box

| Module                   | Purpose                                            |
| ------------------------ | -------------------------------------------------- |
| `reservoir.schema`       | `Reservoir`, `BuildableReservoir`, `WeightedItem`, `WeightedReservoir` |
| `reservoir.algorithms`   | `sample_r`, `sample_l`, `sample_weighted` + step-by-step `add_*` |
| `reservoir.merge`        | `merge_uniform`, `merge_weighted` for distributed sharding |
| `reservoir.simulator`    | uniform / Zipf / weighted-pair stream generators   |
| `reservoir.io_jsonl`     | JSONL codec for snapshots                          |
| `reservoir.cli`          | `info | sample | merge | bench`                  |

## Quick start

```bash
# Sample a reservoir of k=10 from a value file (Algorithm L by default)
python -m reservoir.cli sample --input values.txt --k 10 --output sample.jsonl

# Merge two saved reservoirs (e.g. one per MapReduce shard)
python -m reservoir.cli merge --a shard_a.jsonl --b shard_b.jsonl \
  --output combined.jsonl

# Empirically verify uniformity (k/N guarantee)
python -m reservoir.cli bench --algorithm R --n 1000 --k 50 --trials 500
# → expected_picks_per_item: 25, min: ~11, max: ~40, distinct: 1000
```

```python
import random
from reservoir import sample_r, sample_l, sample_weighted, merge_uniform

# Algorithm R — O(N), easy to reason about
sample = sample_r(stream_of_strings, capacity=100, rng=random.Random(0))

# Algorithm L — O(k · (1 + log(N/k))), much faster for large streams
sample = sample_l(huge_stream, capacity=100, rng=random.Random(0))

# Weighted A-Res — items with higher weights are more likely to land in the sample
weighted = sample_weighted(
    [("urgent", 100.0), ("normal", 1.0), ...], capacity=10,
)

# Distributed: each shard runs its own sampler, then merge once
combined = merge_uniform(shard1, shard2, rng=random.Random(0))
```

## Algorithm summary

| Algorithm    | Cost                  | Reference                       |
| ------------ | --------------------- | ------------------------------- |
| Algorithm R  | O(N) draws            | Vitter (1985)                   |
| Algorithm L  | O(k · (1 + log(N/k))) | Li (1994)                       |
| A-Res        | O(N log k)            | Efraimidis & Spirakis (2006)    |

All three produce a uniform (or weighted-uniform) sample of size
exactly ``k`` from a stream of unknown length, in a single pass, with
no need to know ``N`` in advance.

## Empirical uniformity (Algorithm R + L)

500 independent trials on a stream of N=1000 items, capacity k=50:

| Algorithm | Expected | Min picks | Max picks | Distinct |
| --------- | -------- | --------- | --------- | -------- |
| R         | 25.0     | 11        | 40        | 1000     |
| L         | 25.0     | 14        | 44        | 1000     |

Both stay well within 5σ of the textbook expectation `trials · k / N`,
and both pick every item at least once over 500 trials.

## Merging across shards

When N workers each maintain a local reservoir, the global sample can
be reconstructed without revisiting raw data — pick each output slot
weighted by the shard's ``n_seen``. ``merge_uniform`` does this:

```python
shard1 = sample_r(local_stream_1, capacity=k)
shard2 = sample_r(local_stream_2, capacity=k)
combined = merge_uniform(shard1, shard2)
```

The weighted variant (`merge_weighted`) is *exactly* mergeable —
every per-item priority key is preserved and the top-k by key
survives.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 7 source files clean
pytest                        # 89 tests, all green
```

## References

* Vitter, J. S. (1985). *Random Sampling with a Reservoir*.
  ACM TOMS 11(1): 37–57.
* Li, K. (1994). *Reservoir-Sampling Algorithms of Time Complexity
  O(n(1 + log(N/n)))*. ACM TOMS 20(4): 481–493.
* Efraimidis, P. & Spirakis, P. (2006). *Weighted random sampling
  with a reservoir*. Information Processing Letters 97(5): 181–185.

## License

MIT
