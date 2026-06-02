"""Round-robin partitioner — for keyless records."""

from __future__ import annotations


class RoundRobinPartitioner:
    """Stateful round-robin assignment.

    Use this when records don't carry a meaningful partitioning key
    and you just want even load distribution (e.g. fan-out to workers
    where order doesn't matter).
    """

    __slots__ = ("n_partitions", "_next")

    def __init__(self, n_partitions: int) -> None:
        if n_partitions < 1:
            raise ValueError("n_partitions must be >= 1")
        self.n_partitions = n_partitions
        self._next = 0

    def next_partition(self) -> int:
        p = self._next
        self._next = (self._next + 1) % self.n_partitions
        return p

    def reset(self) -> None:
        self._next = 0


__all__ = ["RoundRobinPartitioner"]
