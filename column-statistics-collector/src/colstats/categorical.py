"""Categorical stats — cardinality + top-K via Space-Saving.

The **Space-Saving** algorithm (Metwally / Agrawal / Abbadi, 2005)
solves the top-K problem in a single pass using only O(K) space.
Worst-case overestimation per slot is bounded by ``N / K`` where
``N`` is the stream size — we expose this as the ``epsilon`` field
on each ``TopKEntry``.

Algorithm sketch:

1. Maintain a fixed-size map ``counter[value] -> count``.
2. On each input value:
   * If ``value`` is already in the map, increment its count.
   * If the map has room (< K entries), insert with count = 1.
   * Otherwise, find the **smallest-count** entry, evict it, and
     replace with ``value`` whose count becomes ``min_count + 1``.
     The evicted entry's count becomes the new ``epsilon`` for the
     replacement.

The map at end-of-stream is the top-K candidate set; the true
top-K is a subset of these K entries with error bound ``epsilon``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from colstats.schema import TopKEntry


@dataclass(slots=True)
class _Slot:
    """One slot in the Space-Saving counter map."""

    count: int
    epsilon: int  # over-count error bound (max actual frequency = count - epsilon)


@dataclass(slots=True)
class SpaceSaving:
    """Space-Saving top-K counter with K slots."""

    k: int
    _slots: dict[str, _Slot] = field(default_factory=dict, init=False)
    _n_seen: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.k < 1:
            raise ValueError(f"k must be >= 1, got {self.k}")

    def add(self, value: str) -> None:
        """Process one input value."""
        self._n_seen += 1
        if value in self._slots:
            self._slots[value].count += 1
            return
        if len(self._slots) < self.k:
            self._slots[value] = _Slot(count=1, epsilon=0)
            return
        # Evict the smallest-count entry.
        smallest_value, smallest_slot = min(
            self._slots.items(),
            key=lambda kv: kv[1].count,
        )
        del self._slots[smallest_value]
        self._slots[value] = _Slot(
            count=smallest_slot.count + 1,
            epsilon=smallest_slot.count,
        )

    def top_k(self) -> list[TopKEntry]:
        """Return the current top-K candidate list, sorted by count desc."""
        entries = [
            TopKEntry(value=v, count=s.count, epsilon=s.epsilon) for v, s in self._slots.items()
        ]
        entries.sort(key=lambda e: (-e.count, e.value))
        return entries

    @property
    def n_seen(self) -> int:
        """Total values processed (incl. duplicates)."""
        return self._n_seen


def top_k(values: list[str], k: int = 10) -> list[TopKEntry]:
    """One-shot top-K over a list of values."""
    ss = SpaceSaving(k=k)
    for v in values:
        ss.add(v)
    return ss.top_k()


def cardinality(values: list[str], cap: int = 10_000) -> tuple[int, bool]:
    """Distinct count over ``values``, capped at ``cap``.

    Returns ``(count, capped)``. When ``count > cap``, the count is
    ``cap + 1`` and ``capped`` is ``True``.
    """
    if cap < 1:
        raise ValueError(f"cap must be >= 1, got {cap}")
    seen: set[str] = set()
    for v in values:
        seen.add(v)
        if len(seen) > cap:
            return cap + 1, True
    return len(seen), False


__all__ = ["SpaceSaving", "cardinality", "top_k"]
