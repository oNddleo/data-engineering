"""Streaming dedup driver: read records, keep first sighting of each key."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bloomdedup.bloom import BloomFilter
from bloomdedup.schema import BloomParams

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


@dataclass(frozen=True, slots=True)
class DedupStats:
    seen: int
    kept: int
    suppressed: int

    @property
    def suppression_rate(self) -> float:
        return self.suppressed / self.seen if self.seen else 0.0


def dedup_stream(
    records: Iterable[str],
    *,
    params: BloomParams | None = None,
    capacity: int = 100_000,
    fpr: float = 0.01,
) -> tuple[list[str], DedupStats]:
    """Eagerly dedupe a stream of string keys.

    Returns the kept-list plus stats. Use ``dedup_iter`` for a streaming
    variant that doesn't materialise the output list.
    """
    bf = BloomFilter(params or BloomParams.for_capacity(capacity, fpr))
    kept: list[str] = []
    seen = 0
    for key in records:
        seen += 1
        if not bf.add(key):
            kept.append(key)
    return kept, DedupStats(seen=seen, kept=len(kept), suppressed=seen - len(kept))


def dedup_iter(
    records: Iterable[str],
    *,
    params: BloomParams | None = None,
    capacity: int = 100_000,
    fpr: float = 0.01,
) -> Iterator[str]:
    """Streaming dedup: yield first-sighting of each key as records arrive."""
    bf = BloomFilter(params or BloomParams.for_capacity(capacity, fpr))
    for key in records:
        if not bf.add(key):
            yield key


__all__ = ["DedupStats", "dedup_iter", "dedup_stream"]
