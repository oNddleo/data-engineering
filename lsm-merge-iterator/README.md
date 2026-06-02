# lsm-merge-iterator

K-way merge of sorted runs — the compaction primitive at the heart of
every LSM-tree (LevelDB, RocksDB, Cassandra, ScyllaDB).

Streaming, single-pass, O(k) memory in the number of runs (independent
of total record count), with last-write-wins and tombstone semantics.

## What it does

Given `k` sorted runs of `Record(key, seq, value, tombstone)`, emit
one record per unique key, picking the **highest `seq`** as the winner
("last-write-wins"). Tombstones with the winning seq drop the key
entirely on final-level compaction, or carry through on intermediate
levels (`keep_tombstones=True`).

```python
from lsmmerge import Record, merge_runs

older = [Record(key="a", seq=1, value="OLD"), Record(key="c", seq=3)]
newer = [Record(key="a", seq=5, value="NEW"), Record(key="b", seq=4)]

list(merge_runs([older, newer]))
# [Record(key="a", seq=5, value="NEW"),
#  Record(key="b", seq=4),
#  Record(key="c", seq=3)]
```

## Quick start

```bash
pip install lsm-merge-iterator

# Generate 4 overlapping sorted runs:
lsmmerge simulate --n-runs 4 --keys-per-run 100 --key-universe 200 \
                  --tombstone-rate 0.1 --seed 0 --output runs/

# Compact them into one sorted output:
lsmmerge merge --input runs/ --output compacted.jsonl
```

## Algorithm

Min-heap keyed by `(key, -seq, run_idx)`:

* Smallest key emerges first.
* Among duplicates, **highest seq** wins (we negate `seq` so the
  heap-min becomes the value-max).
* Each pop advances the source run's iterator, pushing the next
  record onto the heap.
* Memory: O(k) — one slot per input run.

## Tombstone semantics

* Final-level compaction (`keep_tombstones=False`): a tombstone with
  the winning seq removes the key from the output entirely.
* Intermediate-level compaction (`keep_tombstones=True`): the
  tombstone survives so it can continue shadowing older keys in lower
  levels that haven't been compacted yet.

## Design

* Zero runtime dependencies (stdlib `heapq`).
* mypy `--strict`, ruff clean.
* Hypothesis property tests for sortedness, uniqueness, last-write-wins,
  and tombstone consumption.

## License

MIT.
