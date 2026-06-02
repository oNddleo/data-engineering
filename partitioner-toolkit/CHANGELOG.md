# Changelog

## 0.1.0

Initial release.

* `HashModPartitioner` — stable SHA-256-based hash modulo.
* `RangePartitioner` — bisect-driven half-open `[lo, hi)` ranges.
* `ConsistentHashRing` — virtual-node Karger ring with O(log V)
  lookup, idempotent `add_node` / `remove_node`.
* `RoundRobinPartitioner` — stateful cyclic counter.
* `simulator.generate_keys` — deterministic key stream.
* `partitioner` CLI: `info | hash | range | consistent | simulate`.
* JSONL codec for keys and (key, partition) assignments.
* Hypothesis property tests covering range, monotonicity,
  consistent-ring node-in-set, and remove-only-moves-orphans
  invariant.
