# partitioner-toolkit

Shard / partition assignment primitives — pick the right one for the
right job.

| Partitioner       | Use when                                    | Movement on resize       |
| ----------------- | ------------------------------------------- | ------------------------ |
| `HashModPartitioner` | Fixed partition count (Kafka topic)      | ~100 % keys move         |
| `RangePartitioner`   | Keys carry ordering, want co-located scans  | depends on cut points    |
| `ConsistentHashRing` | Elastic cluster (cache, KV store)        | ~1/N keys move           |
| `RoundRobinPartitioner` | Keyless records, even load           | n/a                      |

## Quick start

```bash
pip install partitioner-toolkit

partitioner simulate --n 10000 --alphabet 5000 --seed 0 --output keys.jsonl

partitioner hash --input keys.jsonl --output by_hash.jsonl --partitions 8
# → {"n_keys": 10000, "partitions": 8, "counts": {"0": 1259, "1": 1255, ...}}

partitioner consistent --input keys.jsonl --output by_node.jsonl \
                       --nodes a b c d --replicas 128
# → {"n_keys": 10000, "counts": {"a": 2511, "b": 2483, "c": 2540, "d": 2466}}

partitioner range --boundaries 10,20,30 5 15 25 35
# → {"boundaries": [10,20,30], "n_partitions": 4, "sample": {"5":0,"15":1,"25":2,"35":3}}
```

## Consistent hashing

`ConsistentHashRing` uses the textbook Karger-et-al. construction with
virtual nodes:

* Each real node is placed on the 64-bit ring at `replicas` (default
  128) positions, derived from `sha256(f"{node}#{i}")`.
* A key's owner is the next node clockwise from `sha256(key)`.
* Adding or removing a node moves only ~`1/N` of the keys, not all of
  them.

```python
from partitioner import ConsistentHashRing

ring = ConsistentHashRing(["cache-a", "cache-b", "cache-c"], replicas=128)
ring.node_for("user:42")     # → "cache-b"
ring.add_node("cache-d")      # only ~25 % of keys re-home
ring.remove_node("cache-a")   # only cache-a's keys re-home
```

## Hash stability

We deliberately don't use Python's built-in `hash()` because it's
randomised per interpreter run — a key would land on a different
partition every restart. All partitioners use **SHA-256 truncated to
8 bytes**, which is deterministic across processes and runs.

## License

MIT.
