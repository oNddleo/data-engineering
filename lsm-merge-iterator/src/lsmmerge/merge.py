"""k-way merge of sorted runs with last-write-wins semantics.

Uses a min-heap keyed by ``(key, -seq, run_idx)`` so that:

* The smallest key emerges first.
* Among duplicates of the same key, the **highest seq** comes first
  (we negate ``seq`` to invert the comparator on a min-heap).
* ``run_idx`` is the final tiebreaker, deterministic for equal
  ``(key, seq)`` pairs (which shouldn't happen in well-formed runs
  but we don't crash on it).

The merge is single-pass and streaming — memory is O(k) where k is the
number of input runs, independent of total record count.
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from lsmmerge.schema import Record


def merge_runs(
    runs: Iterable[Iterable[Record]],
    *,
    keep_tombstones: bool = False,
) -> Iterator[Record]:
    """Merge k sorted runs into one sorted stream.

    Args:
        runs: list of iterables, each yielding ``Record`` in
            non-decreasing key order. Within a single run, the same key
            may appear with different seqs (rare but allowed); the
            higher seq wins.
        keep_tombstones: if ``False`` (default), tombstones are
            consumed during merge (final-level compaction). If ``True``,
            tombstones survive into the output (intermediate-level
            compaction that must still shadow older runs underneath).

    Yields:
        One winning ``Record`` per unique key, in ascending key order.
    """
    iters: list[Iterator[Record]] = [iter(r) for r in runs]
    # Heap entries: (key, -seq, run_idx, record)
    heap: list[tuple[str, int, int, Record]] = []
    for idx, it in enumerate(iters):
        rec = next(it, None)
        if rec is not None:
            heapq.heappush(heap, (rec.key, -rec.seq, idx, rec))

    current_key: str | None = None
    winner: Record | None = None

    while heap:
        key, _, idx, rec = heapq.heappop(heap)
        # Advance the source run.
        nxt = next(iters[idx], None)
        if nxt is not None:
            if nxt.key < rec.key:
                raise ValueError(
                    f"run {idx} not sorted: {nxt.key!r} after {rec.key!r}",
                )
            heapq.heappush(heap, (nxt.key, -nxt.seq, idx, nxt))

        if key != current_key:
            # New key: flush the previous winner (if any).
            if winner is not None and (keep_tombstones or not winner.tombstone):
                yield winner
            current_key = key
            winner = rec
        elif winner is None or rec.seq > winner.seq:
            # Same key, higher seq — promote the new record. This matters
            # for intra-run duplicates (heap pops the older one first).
            winner = rec

    if winner is not None and (keep_tombstones or not winner.tombstone):
        yield winner


__all__ = ["merge_runs"]
