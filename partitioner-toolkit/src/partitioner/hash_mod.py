"""Hash-modulo partitioner — the simplest possible scheme.

``partition_for(key) = hash(key) % n_partitions``

Pros: fast (one hash + one modulo), perfectly uniform with a good hash.
Cons: changing ``n_partitions`` reshuffles **all** keys. Use this only
when the partition count is fixed (e.g. Kafka topic with N partitions)
— for elastic cluster sizing use ``consistent.ConsistentHashRing``.

We use SHA-256 truncated to 8 bytes for the underlying hash — much
more uniform than Python's built-in ``hash()`` (which is randomised
per-interpreter and so not deterministic across runs).
"""

from __future__ import annotations

import hashlib


def _hash64(key: str) -> int:
    """Stable 64-bit hash for partitioning.

    Python's built-in ``hash()`` is randomised per interpreter run, so
    a key would land on a different partition every restart. SHA-256
    truncated to 8 bytes is deterministic and uniformly distributed.
    """
    return int.from_bytes(
        hashlib.sha256(key.encode("utf-8")).digest()[:8],
        "big",
    )


class HashModPartitioner:
    """Stateless hash-modulo partitioner."""

    __slots__ = ("n_partitions",)

    def __init__(self, n_partitions: int) -> None:
        if n_partitions < 1:
            raise ValueError("n_partitions must be >= 1")
        self.n_partitions = n_partitions

    def partition_for(self, key: str) -> int:
        return _hash64(key) % self.n_partitions


__all__ = ["HashModPartitioner"]
