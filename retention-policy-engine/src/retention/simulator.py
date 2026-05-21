"""Synthetic record generator."""

from __future__ import annotations

import random
from dataclasses import dataclass

from retention.schema import Record


@dataclass(frozen=True, slots=True)
class SimStats:
    n_records: int
    total_bytes: int
    tag_counts: dict[str, int]


_TAGS = ["raw", "processed", "archived", "hot", "cold", "tmp"]


def generate(
    n: int = 100,
    seed: int = 0,
    now_ms: int = 1_000_000,
    max_age_ms: int = 86_400_000,
    max_size_bytes: int = 1_048_576,
) -> list[Record]:
    """Generate *n* synthetic records."""
    if n <= 0:
        raise ValueError("n must be positive")
    rng = random.Random(seed)
    records: list[Record] = []
    for i in range(n):
        age = rng.randint(0, max_age_ms)
        size = rng.randint(100, max_size_bytes)
        n_tags = rng.randint(0, 3)
        tags = frozenset(rng.sample(_TAGS, k=min(n_tags, len(_TAGS))))
        records.append(
            Record(
                key=f"rec-{i:05d}",
                created_at_ms=max(0, now_ms - age),
                size_bytes=size,
                tags=tags,
            )
        )
    return records


def summarise(records: list[Record]) -> SimStats:
    tag_counts: dict[str, int] = {}
    for r in records:
        for t in r.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    return SimStats(
        n_records=len(records),
        total_bytes=sum(r.size_bytes for r in records),
        tag_counts=tag_counts,
    )
