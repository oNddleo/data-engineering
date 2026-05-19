"""Hypothesis property tests for t-digest invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tdigest.digest import add, build, cdf, freeze, merge, quantile
from tdigest.io_jsonl import digest_from_dict, digest_to_dict
from tdigest.scale import k as scale_k
from tdigest.scale import max_combined_weight, q_from_k
from tdigest.simulator import exact_quantile

value_strategy = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)


# ---------- Scale function --------------------------------------------------


@given(
    st.floats(min_value=0.0, max_value=1.0),
    st.floats(min_value=10.0, max_value=1000.0),
)
@settings(max_examples=80)
def test_k_inverse(q: float, compression: float) -> None:
    """q_from_k(k(q)) ≈ q (rounding tolerance)."""
    recovered = q_from_k(scale_k(q, compression), compression)
    assert abs(recovered - q) < 1e-6


@given(
    st.floats(min_value=0.0, max_value=0.99),
    st.floats(min_value=10.0, max_value=1000.0),
)
@settings(max_examples=60)
def test_k_monotonic(q: float, compression: float) -> None:
    """k is strictly increasing in q."""
    assert scale_k(q, compression) < scale_k(q + 0.01, compression)


@given(
    st.floats(min_value=0.0, max_value=1.0),
    st.floats(min_value=1.0, max_value=100_000.0),
    st.floats(min_value=10.0, max_value=1000.0),
)
@settings(max_examples=50)
def test_size_bound_nonnegative(q: float, total: float, compression: float) -> None:
    assert max_combined_weight(q, total, compression) >= 0


# ---------- Digest invariants -----------------------------------------------


@given(st.lists(value_strategy, min_size=1, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_total_weight_equals_count(values: list[float]) -> None:
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    assert snap.total_weight == len(values)


@given(st.lists(value_strategy, min_size=1, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_min_max_exact(values: list[float]) -> None:
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    assert snap.min_value == min(values)
    assert snap.max_value == max(values)


@given(st.lists(value_strategy, min_size=2, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_quantile_zero_and_one(values: list[float]) -> None:
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    assert quantile(snap, 0.0) == min(values)
    assert quantile(snap, 1.0) == max(values)


@given(st.lists(value_strategy, min_size=2, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_quantile_monotonic(values: list[float]) -> None:
    """Quantile is non-decreasing in q."""
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    samples = [quantile(snap, q) for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    assert samples == sorted(samples)


@given(st.lists(value_strategy, min_size=2, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_cdf_monotonic(values: list[float]) -> None:
    """cdf is non-decreasing in value."""
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    lo, hi = min(values), max(values)
    if lo == hi:
        return
    probes = [lo + (hi - lo) * f for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
    cdfs = [cdf(snap, p) for p in probes]
    assert cdfs == sorted(cdfs)


@given(st.lists(value_strategy, min_size=1, max_size=100))
@settings(max_examples=20)
def test_jsonl_roundtrip(values: list[float]) -> None:
    td = build(compression=100.0)
    for v in values:
        add(td, v)
    snap = freeze(td)
    restored = digest_from_dict(digest_to_dict(snap))
    assert restored == snap


# ---------- Merge: weight conservation --------------------------------------


@given(
    st.lists(value_strategy, min_size=1, max_size=50),
    st.lists(value_strategy, min_size=1, max_size=50),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_merge_preserves_total_weight(a_vals: list[float], b_vals: list[float]) -> None:
    a = build(compression=100.0)
    for v in a_vals:
        add(a, v)
    b = build(compression=100.0)
    for v in b_vals:
        add(b, v)
    merged = merge(freeze(a), freeze(b))
    assert merged.total_weight == len(a_vals) + len(b_vals)


# ---------- Accuracy on uniform: tighter than 1/compression bound ----------


@given(st.integers(min_value=1_000, max_value=20_000))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10)
def test_median_accurate(n: int) -> None:
    """The median of a sorted 0..n input must be near n/2."""
    td = build(compression=200.0)
    for i in range(n):
        add(td, float(i))
    snap = freeze(td)
    est = quantile(snap, 0.5)
    exact = exact_quantile([float(i) for i in range(n)], 0.5)
    assert abs(est - exact) < n * 0.05
