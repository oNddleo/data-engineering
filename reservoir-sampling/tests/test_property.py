"""Hypothesis property tests for reservoir-sampling invariants."""

from __future__ import annotations

import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from reservoir.algorithms import sample_l, sample_r, sample_weighted
from reservoir.io_jsonl import (
    reservoir_from_dict,
    reservoir_to_dict,
    weighted_from_dict,
    weighted_to_dict,
)
from reservoir.merge import merge_uniform, merge_weighted
from reservoir.schema import Reservoir, WeightedReservoir

value_strategy = st.text(min_size=1, max_size=20)
weight_strategy = st.floats(
    min_value=1e-6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)


# ---------- Algorithm R / L invariants ------------------------------------


@given(st.lists(value_strategy, min_size=0, max_size=200), st.integers(min_value=1, max_value=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_r_n_seen_matches_input(stream: list[str], k: int) -> None:
    res = sample_r(stream, capacity=k, rng=random.Random(0))
    assert res.n_seen == len(stream)


@given(st.lists(value_strategy, min_size=0, max_size=200), st.integers(min_value=1, max_value=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_r_n_kept_capped(stream: list[str], k: int) -> None:
    res = sample_r(stream, capacity=k, rng=random.Random(0))
    assert res.n_kept <= k
    assert res.n_kept <= len(stream)


@given(st.lists(value_strategy, min_size=0, max_size=200), st.integers(min_value=1, max_value=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_r_items_subset_of_stream(stream: list[str], k: int) -> None:
    res = sample_r(stream, capacity=k, rng=random.Random(0))
    assert set(res.items).issubset(set(stream))


@given(st.lists(value_strategy, min_size=0, max_size=200), st.integers(min_value=1, max_value=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_l_n_seen_matches_input(stream: list[str], k: int) -> None:
    res = sample_l(stream, capacity=k, rng=random.Random(0))
    assert res.n_seen == len(stream)


@given(st.lists(value_strategy, min_size=0, max_size=200), st.integers(min_value=1, max_value=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_l_items_subset_of_stream(stream: list[str], k: int) -> None:
    res = sample_l(stream, capacity=k, rng=random.Random(0))
    assert set(res.items).issubset(set(stream))


@given(st.lists(value_strategy, min_size=0, max_size=50), st.integers(min_value=1, max_value=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_underfilled_keeps_all(stream: list[str], k: int) -> None:
    """If the stream length is ≤ k, the reservoir keeps all items."""
    if len(stream) > k:
        return
    res = sample_r(stream, capacity=k, rng=random.Random(0))
    assert sorted(res.items) == sorted(stream)


# ---------- Weighted invariants --------------------------------------------


@given(
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=0, max_size=50),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_weighted_n_seen_matches(pairs: list[tuple[str, float]], k: int) -> None:
    res = sample_weighted(pairs, capacity=k, rng=random.Random(0))
    assert res.n_seen == len(pairs)


@given(
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=0, max_size=50),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_weighted_kept_capped(pairs: list[tuple[str, float]], k: int) -> None:
    res = sample_weighted(pairs, capacity=k, rng=random.Random(0))
    assert len(res.items) <= k
    assert len(res.items) <= len(pairs)


@given(
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=1, max_size=30),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_weighted_keys_sorted_ascending(
    pairs: list[tuple[str, float]],
    k: int,
) -> None:
    res = sample_weighted(pairs, capacity=k, rng=random.Random(0))
    for i in range(1, len(res.items)):
        assert res.items[i - 1].key <= res.items[i].key


# ---------- JSONL round-trip ----------------------------------------------


@given(
    st.lists(value_strategy, min_size=0, max_size=50),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_reservoir_jsonl_roundtrip(stream: list[str], k: int) -> None:
    res = sample_r(stream, capacity=k, rng=random.Random(0))
    assert reservoir_from_dict(reservoir_to_dict(res)) == res


@given(
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=0, max_size=20),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_weighted_jsonl_roundtrip(pairs: list[tuple[str, float]], k: int) -> None:
    res = sample_weighted(pairs, capacity=k, rng=random.Random(0))
    restored = weighted_from_dict(weighted_to_dict(res))
    assert restored.items == res.items
    assert restored.n_seen == res.n_seen


# ---------- Merge conservation --------------------------------------------


@given(
    st.lists(value_strategy, min_size=1, max_size=50),
    st.lists(value_strategy, min_size=1, max_size=50),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_merge_uniform_preserves_n_seen(
    stream_a: list[str],
    stream_b: list[str],
    k: int,
) -> None:
    a = sample_r(stream_a, capacity=k, rng=random.Random(0))
    b = sample_r(stream_b, capacity=k, rng=random.Random(1))
    merged = merge_uniform(a, b, rng=random.Random(2))
    assert merged.n_seen == a.n_seen + b.n_seen


@given(
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=1, max_size=20),
    st.lists(st.tuples(value_strategy, weight_strategy), min_size=1, max_size=20),
    st.integers(min_value=1, max_value=8),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=15)
def test_merge_weighted_preserves_totals(
    pairs_a: list[tuple[str, float]],
    pairs_b: list[tuple[str, float]],
    k: int,
) -> None:
    a = sample_weighted(pairs_a, capacity=k, rng=random.Random(0))
    b = sample_weighted(pairs_b, capacity=k, rng=random.Random(1))
    merged = merge_weighted(a, b)
    assert merged.n_seen == a.n_seen + b.n_seen
    assert (
        abs(
            merged.total_weight_seen - (a.total_weight_seen + b.total_weight_seen),
        )
        < 1e-6
    )


# ---------- Empty / edge invariants ----------------------------------------


def test_reservoir_empty_invariants() -> None:
    res = Reservoir(capacity=5, items=(), n_seen=0)
    assert res.n_kept == 0
    assert res.fill_ratio == 0.0


def test_weighted_empty_invariants() -> None:
    wr = WeightedReservoir(capacity=5)
    assert wr.n_seen == 0
    assert wr.total_weight_seen == 0.0
