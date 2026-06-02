"""Core record type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Record:
    """A data record subject to retention policy."""

    key: str
    created_at_ms: int  # epoch milliseconds
    size_bytes: int
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key must be non-empty")
        if self.created_at_ms < 0:
            raise ValueError("created_at_ms must be >= 0")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be >= 0")
