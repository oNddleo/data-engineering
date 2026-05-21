"""Core eviction engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from retention.schema import Record

from retention.policy import Policy, PolicyKind


@dataclass(frozen=True, slots=True)
class EvictionResult:
    kept: list[Record]
    evicted: list[Record]
    bytes_freed: int
    records_freed: int


def _matches_tag_filter(record: Record, tag_filter: frozenset[str]) -> bool:
    """Return True if this record is subject to the policy (tag-matched)."""
    if not tag_filter:
        return True
    return bool(record.tags & tag_filter)


def _apply_ttl(
    records: list[Record], policy: Policy, now_ms: int
) -> tuple[list[Record], list[Record]]:
    cutoff = now_ms - policy.ttl_ms
    kept = [
        r
        for r in records
        if not _matches_tag_filter(r, policy.tag_filter) or r.created_at_ms >= cutoff
    ]
    evicted = [
        r
        for r in records
        if _matches_tag_filter(r, policy.tag_filter) and r.created_at_ms < cutoff
    ]
    return kept, evicted


def _apply_max_count(records: list[Record], policy: Policy) -> tuple[list[Record], list[Record]]:
    subject = [r for r in records if _matches_tag_filter(r, policy.tag_filter)]
    exempt = [r for r in records if not _matches_tag_filter(r, policy.tag_filter)]
    # Sort newest-first; keep first N
    subject_sorted = sorted(subject, key=lambda r: r.created_at_ms, reverse=True)
    kept_subject = subject_sorted[: policy.count_limit]
    evicted_subject = subject_sorted[policy.count_limit :]
    return exempt + kept_subject, evicted_subject


def _apply_max_size(records: list[Record], policy: Policy) -> tuple[list[Record], list[Record]]:
    subject = [r for r in records if _matches_tag_filter(r, policy.tag_filter)]
    exempt = [r for r in records if not _matches_tag_filter(r, policy.tag_filter)]
    # Evict oldest first; keep newest until budget exhausted
    subject_sorted = sorted(subject, key=lambda r: r.created_at_ms, reverse=True)
    kept_subject: list[Record] = []
    evicted_subject: list[Record] = []
    total = 0
    for r in subject_sorted:
        if total + r.size_bytes <= policy.size_limit:
            kept_subject.append(r)
            total += r.size_bytes
        else:
            evicted_subject.append(r)
    return exempt + kept_subject, evicted_subject


def _apply_single(
    records: list[Record], policy: Policy, now_ms: int
) -> tuple[list[Record], list[Record]]:
    if policy.kind == PolicyKind.TTL:
        return _apply_ttl(records, policy, now_ms)
    if policy.kind == PolicyKind.MAX_COUNT:
        return _apply_max_count(records, policy)
    if policy.kind == PolicyKind.MAX_SIZE:
        return _apply_max_size(records, policy)
    # COMPOSITE: union of all sub-policy evictions
    all_evicted: set[str] = set()
    for sub in policy.sub_policies:
        _, sub_evicted = _apply_single(records, sub, now_ms)
        all_evicted.update(r.key for r in sub_evicted)
    kept = [r for r in records if r.key not in all_evicted]
    evicted = [r for r in records if r.key in all_evicted]
    return kept, evicted


def apply_policy(records: list[Record], policy: Policy, now_ms: int) -> EvictionResult:
    """Apply a retention policy to a list of records."""
    kept, evicted = _apply_single(records, policy, now_ms)
    return EvictionResult(
        kept=kept,
        evicted=evicted,
        bytes_freed=sum(r.size_bytes for r in evicted),
        records_freed=len(evicted),
    )
