# dedup-with-bloom

Bloom-filter-backed streaming deduplicator. Probabilistic membership
for at-most-once delivery, with bounded false-positive rate.

## What it does

* **`BloomParams.for_capacity(n, fpr=0.01)`** — calculate optimal
  bit-array size and number of hashes for `n` items at target FPR.
* **`BloomFilter`** — fixed-size bit array using double hashing
  (Kirsch-Mitzenmacher) over SHA-256 + MD5. Only two hash evaluations
  per item, regardless of k.
* **`dedup_stream / dedup_iter`** — given an iterable of keys, emit
  first-sighting of each (eagerly or lazily).

## Quick start

```bash
pip install dedup-with-bloom

bloomdedup params --capacity 100000 --fpr 0.001
# → {"capacity": 100000, "fpr": 0.001, "m_bits": 1437760, "m_bytes": 179720, "k_hashes": 10}

bloomdedup simulate --n 100000 --unique 1000 --duplicate-rate 0.9 --seed 0 \
                    --output raw.jsonl
bloomdedup dedup --input raw.jsonl --output unique.jsonl \
                 --capacity 100000 --fpr 0.001
# → {"seen": 100000, "kept": 1000, "suppressed": 99000, "suppression_rate": 0.99}
```

## Library

```python
from bloomdedup import dedup_stream

kept, stats = dedup_stream(["a", "b", "a", "c"], capacity=100, fpr=0.01)
# kept == ["a", "b", "c"]
# stats.seen == 4, stats.kept == 3, stats.suppressed == 1
```

## Sizing math

```
m = -n · ln(p) / (ln 2)²       # bit-array size
k = (m/n) · ln 2               # number of hashes
```

Rule of thumb: **~9.6 bits per item for 1 % FPR**. For 100 000 items
at 1 % that's ~120 KiB — tiny next to the alternative (a Python set
of the same items, ~10 MB).

## Hashing trick

Instead of running k independent hash functions, we use just two
(SHA-256 + MD5) and synthesise the rest:

    h_i(x) = (h1(x) + i · h2(x)) mod m

Asymptotic FPR is unchanged (Kirsch & Mitzenmacher 2006), but each
`add`/`contains` costs only two hash evaluations instead of k.

## False positives, false negatives

* **False negatives are impossible.** If the filter says "no", the
  item was never added.
* **False positives are bounded by the target FPR**, achieved when
  the filter is loaded to its declared capacity. Loading past
  capacity degrades the FPR; the `fill_ratio` property is a
  real-time saturation indicator.

## License

MIT.
