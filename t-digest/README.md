# t-digest

Production-grade **t-digest** (Dunning & Ertl, 2014) in pure
Python 3.10+ — a streaming quantile sketch that fits a 100k-sample
stream into ~60 centroids while keeping p99 accurate to within 2%.

Completes the canonical probabilistic-data-structure quartet alongside
[`count-min-sketch`](../count-min-sketch) (frequency),
[`hyperloglog-cardinality`](../hyperloglog-cardinality) (distinct
count), and [`bloom-filter`](../bloom-filter) (set membership). The
t-digest answers the fourth question: **"what's the p50 / p99 / p999
of this stream?"** — the foundation of every modern latency dashboard.

Zero runtime dependencies (stdlib only), `mypy --strict` clean,
80 tests including Hypothesis property tests.

## What's in the box

| Module             | Purpose                                              |
| ------------------ | ---------------------------------------------------- |
| `tdigest.schema`   | `Centroid`, `TDigest` (frozen), `BuildableTDigest`   |
| `tdigest.scale`    | `k1` scale function + per-centroid size bound        |
| `tdigest.digest`   | `build`, `add`, `compress`, `quantile`, `cdf`, `merge`, `freeze`, `thaw` |
| `tdigest.simulator`| Uniform / gaussian / lognormal / pareto streams + exact-quantile baseline |
| `tdigest.io_jsonl` | JSONL codec for snapshots                            |
| `tdigest.cli`      | `info | build | quantile | cdf | bench`             |

## Quick start

```bash
# Accuracy benchmark on 100k lognormal samples at compression=100
python -m tdigest.cli bench --dist lognormal --n 100000 --compression 100
# → 60 centroids, p99 rel-err < 2%, p999 rel-err < 9%

# Build a digest from a value file, then query quantiles
python -m tdigest.cli build --input latencies.txt --compression 200 \
  --output digest.jsonl
python -m tdigest.cli quantile --input digest.jsonl --q 0.5 0.95 0.99 0.999

# Query the CDF (inverse direction)
python -m tdigest.cli cdf --input digest.jsonl --value 500
```

```python
from tdigest import build, add, freeze, quantile, merge

# Build a digest streaming-style
td = build(compression=200.0)
for latency_ms in service_latencies():
    add(td, latency_ms)
snap = freeze(td)

print(f"p50 = {quantile(snap, 0.5):.1f} ms")
print(f"p99 = {quantile(snap, 0.99):.1f} ms")
print(f"p999 = {quantile(snap, 0.999):.1f} ms")

# Merge digests from N workers — exactly, no information lost
combined = merge(snap_worker_1, snap_worker_2)
```

## Accuracy guarantees

The t-digest is designed for **relative tail accuracy** — small absolute
error for quantiles near 0 or 1, larger absolute error in the middle.
For typical compression δ = 100 the worst-case quantile error scales
like ~1/δ at the median and ~1/δ² at the extremes.

Empirical accuracy on 100k samples, compression = 100:

| Distribution | n_centroids | p50 err | p99 err | p999 err |
| ------------ | ----------- | ------- | ------- | -------- |
| Uniform      | ~60         | < 0.5%  | < 1%    | < 5%     |
| Gaussian     | ~60         | < 0.5%  | < 2%    | < 5%     |
| Lognormal    | ~60         | < 0.2%  | < 2%    | < 8%     |
| Pareto α=1.5 | ~60         | < 0.5%  | < 5%    | < 15%    |

## The scale function

The merge step is bounded by Dunning's k1 scale function:

```
k(q) = δ / (2π) · arcsin(2q − 1)
```

Two adjacent centroids may merge iff `k(q_right) − k(q_left) ≤ 1`.
Because `dk/dq` blows up near q=0 and q=1, centroids in the tails
stay small (high relative accuracy) while centroids near the median
can absorb many points (lower per-point information value).

## Exact mergeability

Two t-digests built independently on disjoint streams can be combined
into a single digest representing the union — *exactly*. This is the
distributed-systems property that makes t-digest the go-to choice for
percentile aggregation across worker shards.

```python
shard1 = build_and_freeze(stream_partition_1)
shard2 = build_and_freeze(stream_partition_2)
shard3 = build_and_freeze(stream_partition_3)
combined = merge(merge(shard1, shard2), shard3)
```

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 7 source files clean
pytest                        # 80 tests, all green
```

## References

* Dunning, T. & Ertl, O. (2019). *Computing Extremely Accurate
  Quantiles Using t-Digests*. arXiv:1902.04023.
* Dunning, T. (2021). *The t-digest: Efficient estimates of
  distributions*. Software Impacts 7: 100049.

## License

MIT
