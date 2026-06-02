"""Range partitioner — keyed by sorted boundary list.

Used when keys carry intrinsic ordering (timestamps, lex'd identifiers)
and you want **co-located** scans. The boundaries are an ascending
list of length ``n_partitions - 1``:

* boundaries ``[10, 20, 30]`` → 4 partitions:
  ``(-inf, 10), [10, 20), [20, 30), [30, +inf)``

Keys equal to a boundary go to the **right** partition (half-open
``[lo, hi)`` semantics). Lookup is O(log n) via ``bisect_right``.
"""

from __future__ import annotations

import bisect


class RangePartitioner:
    """Range partitioner over comparable integer keys.

    Boundaries must be strictly ascending; validated on construction.
    """

    __slots__ = ("_boundaries",)

    def __init__(self, boundaries: list[int]) -> None:
        for i in range(len(boundaries) - 1):
            if boundaries[i] >= boundaries[i + 1]:
                raise ValueError("boundaries must be strictly ascending")
        self._boundaries = list(boundaries)

    @property
    def n_partitions(self) -> int:
        return len(self._boundaries) + 1

    @property
    def boundaries(self) -> list[int]:
        return list(self._boundaries)

    def partition_for(self, key: int) -> int:
        """Return the 0-indexed partition for ``key`` (half-open semantics)."""
        return bisect.bisect_right(self._boundaries, key)


__all__ = ["RangePartitioner"]
