"""Retention policy definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyKind(str, Enum):
    TTL = "TTL"  # expire records older than ttl_ms
    MAX_COUNT = "MAX_COUNT"  # keep only the N newest records
    MAX_SIZE = "MAX_SIZE"  # keep total size below max_bytes (evict oldest first)
    COMPOSITE = "COMPOSITE"  # union eviction: record evicted if any sub-policy evicts it


@dataclass(frozen=True, slots=True)
class Policy:
    """A single retention rule."""

    kind: PolicyKind
    ttl_ms: int = 0  # for TTL
    count_limit: int = 0  # for MAX_COUNT
    size_limit: int = 0  # for MAX_SIZE
    sub_policies: tuple[Policy, ...] = field(default_factory=tuple)
    tag_filter: frozenset[str] = frozenset()  # empty = apply to all

    def __post_init__(self) -> None:
        if self.kind == PolicyKind.TTL and self.ttl_ms <= 0:
            raise ValueError("TTL policy requires ttl_ms > 0")
        if self.kind == PolicyKind.MAX_COUNT and self.count_limit <= 0:
            raise ValueError("MAX_COUNT policy requires count_limit > 0")
        if self.kind == PolicyKind.MAX_SIZE and self.size_limit <= 0:
            raise ValueError("MAX_SIZE policy requires size_limit > 0")
        if self.kind == PolicyKind.COMPOSITE and not self.sub_policies:
            raise ValueError("COMPOSITE policy requires at least one sub-policy")

    @classmethod
    def ttl(cls, ttl_ms: int, tag_filter: frozenset[str] = frozenset()) -> Policy:
        return cls(kind=PolicyKind.TTL, ttl_ms=ttl_ms, tag_filter=tag_filter)

    @classmethod
    def max_count(cls, n: int, tag_filter: frozenset[str] = frozenset()) -> Policy:
        return cls(kind=PolicyKind.MAX_COUNT, count_limit=n, tag_filter=tag_filter)

    @classmethod
    def max_size(cls, max_bytes: int, tag_filter: frozenset[str] = frozenset()) -> Policy:
        return cls(kind=PolicyKind.MAX_SIZE, size_limit=max_bytes, tag_filter=tag_filter)

    @classmethod
    def composite(cls, *policies: Policy) -> Policy:
        return cls(kind=PolicyKind.COMPOSITE, sub_policies=policies)
