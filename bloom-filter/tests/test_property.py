"""Hypothesis property tests for Bloom filter invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bloom.counting import (
    add_counting,
    build_counting,
    contains_counting,
    remove_counting,
)
from bloom.filter import (
    add,
    build,
    contains,
    freeze,
    intersect_estimate,
    thaw,
    union,
)
from bloom.io_jsonl import filter_from_dict, filter_to_dict
from bloom.sizing import estimate_fpr, optimal_n_hashes, optimal_size_bits

value_strategy = st.text(min_size=1, max_size=40)


@given(st.lists(value_strategy, min_size=1, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_no_false_negatives_property(values: list[str]) -> None:
    """No matter what values we insert, every one must contain() True."""
    bf = build(capacity=max(10, len(values) * 2), target_fpr=0.01)
    for v in values:
        add(bf, v)
    for v in values:
        assert contains(bf, v) is True


@given(st.lists(value_strategy, min_size=1, max_size=100))
@settings(max_examples=30)
def test_freeze_thaw_idempotent(values: list[str]) -> None:
    bf = build(capacity=max(10, len(values) * 2), target_fpr=0.01)
    for v in values:
        add(bf, v)
    snap = freeze(bf)
    snap2 = freeze(thaw(snap, capacity=100, target_fpr=0.01))
    assert snap == snap2


@given(st.lists(value_strategy, min_size=1, max_size=100))
@settings(max_examples=30)
def test_jsonl_round_trip_property(values: list[str]) -> None:
    bf = build(capacity=max(10, len(values) * 2), target_fpr=0.01)
    for v in values:
        add(bf, v)
    snap = freeze(bf)
    restored = filter_from_dict(filter_to_dict(snap))
    assert restored == snap


@given(
    st.lists(value_strategy, min_size=1, max_size=50),
    st.lists(value_strategy, min_size=1, max_size=50),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_union_preserves_both_sides(a_values: list[str], b_values: list[str]) -> None:
    a = build(capacity=200, target_fpr=0.01)
    b = build(capacity=200, target_fpr=0.01)
    for v in a_values:
        add(a, v)
    for v in b_values:
        add(b, v)
    u = union(freeze(a), freeze(b))
    for v in a_values + b_values:
        assert contains(u, v) is True


@given(
    st.lists(value_strategy, min_size=1, max_size=50),
    st.lists(value_strategy, min_size=1, max_size=50),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_intersect_preserves_overlap(a_values: list[str], b_values: list[str]) -> None:
    a = build(capacity=200, target_fpr=0.01)
    b = build(capacity=200, target_fpr=0.01)
    for v in a_values:
        add(a, v)
    for v in b_values:
        add(b, v)
    i = intersect_estimate(freeze(a), freeze(b))
    overlap = set(a_values) & set(b_values)
    for v in overlap:
        assert contains(i, v) is True


@given(
    st.integers(min_value=10, max_value=10_000),
    st.floats(min_value=1e-4, max_value=0.1, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30)
def test_sizing_at_capacity_meets_target(capacity: int, target_fpr: float) -> None:
    """At exactly capacity items, estimated FPR should be near target."""
    m = optimal_size_bits(capacity, target_fpr)
    k = optimal_n_hashes(m, capacity)
    actual = estimate_fpr(m, k, capacity)
    # Within 2× of target (rounding of k introduces some slack).
    assert actual <= 2 * target_fpr


@given(st.lists(value_strategy, min_size=1, max_size=50, unique=True))
@settings(max_examples=20)
def test_counting_add_remove_membership(values: list[str]) -> None:
    cb = build_counting(capacity=200, target_fpr=0.01)
    for v in values:
        add_counting(cb, v)
    # Remove half.
    half = len(values) // 2
    for v in values[:half]:
        remove_counting(cb, v)
    # Latter half must still be present.
    for v in values[half:]:
        assert contains_counting(cb, v) is True
