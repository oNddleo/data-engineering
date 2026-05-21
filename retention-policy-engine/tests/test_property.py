"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from retention.engine import apply_policy
from retention.policy import Policy
from retention.schema import Record


def _records(ages_ms: list[int], size: int = 1000) -> list[Record]:
    return [
        Record(key=f"r{i}", created_at_ms=1_000_000 - a, size_bytes=size)
        for i, a in enumerate(ages_ms)
    ]


@given(st.lists(st.integers(min_value=0, max_value=10_000), min_size=0, max_size=50))
@settings(max_examples=200)
def test_ttl_kept_plus_evicted_equals_total(ages_ms: list[int]) -> None:
    records = _records(ages_ms)
    policy = Policy.ttl(ttl_ms=5_000)
    result = apply_policy(records, policy, now_ms=1_000_000)
    assert len(result.kept) + len(result.evicted) == len(records)


@given(
    st.lists(st.integers(min_value=0, max_value=10_000), min_size=1, max_size=50),
    st.integers(min_value=1, max_value=20),
)
@settings(max_examples=200)
def test_max_count_never_exceeds_n(ages_ms: list[int], n: int) -> None:
    records = _records(ages_ms)
    policy = Policy.max_count(n=n)
    result = apply_policy(records, policy, now_ms=1_000_000)
    assert len(result.kept) <= n


@given(
    st.lists(st.integers(min_value=100, max_value=5_000), min_size=1, max_size=30),
    st.integers(min_value=500, max_value=20_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_max_size_total_within_limit(sizes: list[int], max_bytes: int) -> None:
    records = [
        Record(key=f"r{i}", created_at_ms=i * 100, size_bytes=s) for i, s in enumerate(sizes)
    ]
    policy = Policy.max_size(max_bytes=max_bytes)
    result = apply_policy(records, policy, now_ms=1_000_000)
    kept_bytes = sum(r.size_bytes for r in result.kept)
    assert kept_bytes <= max_bytes


@given(st.lists(st.integers(min_value=0, max_value=10_000), min_size=0, max_size=30))
@settings(max_examples=100)
def test_bytes_freed_matches_evicted(ages_ms: list[int]) -> None:
    records = _records(ages_ms, size=512)
    policy = Policy.ttl(ttl_ms=3_000)
    result = apply_policy(records, policy, now_ms=1_000_000)
    assert result.bytes_freed == sum(r.size_bytes for r in result.evicted)
