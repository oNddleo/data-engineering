"""Hypothesis property tests for the Bloom filter and dedup driver."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bloomdedup.bloom import BloomFilter
from bloomdedup.dedup import dedup_stream
from bloomdedup.schema import BloomParams

_key = st.text(min_size=1, max_size=20)


@given(st.lists(_key, min_size=0, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_no_false_negatives(items: list[str]) -> None:
    """Anything added must be reported present."""
    bf = BloomFilter(BloomParams.for_capacity(max(1, len(items)) * 2, fpr=0.01))
    for it in items:
        bf.add(it)
    for it in items:
        assert it in bf


@given(st.lists(_key, min_size=0, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_dedup_kept_is_unique(items: list[str]) -> None:
    """Kept records have no duplicates."""
    kept, _ = dedup_stream(items, capacity=max(1, len(items)) * 2, fpr=0.001)
    assert len(kept) == len(set(kept))


@given(st.lists(_key, min_size=0, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_dedup_kept_subset_of_inputs(items: list[str]) -> None:
    """Every kept record came from the input."""
    kept, _ = dedup_stream(items, capacity=max(1, len(items)) * 2, fpr=0.001)
    assert set(kept).issubset(set(items))


@given(st.lists(_key, min_size=0, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_dedup_stats_consistent(items: list[str]) -> None:
    """seen = kept + suppressed."""
    kept, stats = dedup_stream(items, capacity=max(1, len(items)) * 2, fpr=0.001)
    assert stats.seen == stats.kept + stats.suppressed
    assert stats.kept == len(kept)
    assert stats.seen == len(items)


@given(st.lists(_key, min_size=0, max_size=100, unique=True))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_distinct_inputs_all_kept_under_low_fpr(items: list[str]) -> None:
    """With well-sized Bloom filter (10x capacity, 0.0001 FPR), all distinct
    inputs should typically survive — false positives are statistically
    unlikely at this oversizing."""
    if not items:
        return
    kept, _ = dedup_stream(items, capacity=max(1, len(items)) * 10, fpr=0.0001)
    # Allow up to 1 false positive at this scale.
    assert len(kept) >= len(items) - 1


@given(
    st.integers(min_value=10, max_value=1000),
    st.floats(min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_params_sane(capacity: int, fpr: float) -> None:
    p = BloomParams.for_capacity(capacity, fpr=fpr)
    assert p.m_bits > 0
    assert p.k_hashes >= 1
    assert p.m_bits % 8 == 0
