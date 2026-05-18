"""Hypothesis properties — invariants across profiler subsystems."""

from __future__ import annotations

import statistics
from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from colstats.categorical import SpaceSaving, cardinality, top_k
from colstats.drift import psi
from colstats.histogram import equi_depth, equi_width, maxdiff, reproject
from colstats.numeric import WelfordAccumulator
from colstats.profile import collect_profile
from colstats.schema import ColumnKind

# ---------- Welford ----------------------------------------------------------


@given(
    values=st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=100,
    ),
)
@settings(max_examples=30)
def test_property_welford_matches_stdlib(values: list[float]) -> None:
    """Welford std-dev matches statistics.stdev within floating-point precision."""
    w = WelfordAccumulator()
    for v in values:
        w.add(v)
    expected = statistics.stdev(values)
    assert abs(w.std - expected) < max(1e-6, abs(expected) * 1e-9)


@given(
    values=st.lists(
        st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=20)
def test_property_welford_mean_matches(values: list[float]) -> None:
    w = WelfordAccumulator()
    for v in values:
        w.add(v)
    expected = sum(values) / len(values)
    assert abs(w.mean - expected) < 1e-6


# ---------- Histograms -------------------------------------------------------


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=200,
    ),
    n_bins=st.integers(min_value=2, max_value=20),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_equi_width_total_preserved(
    values: list[float],
    n_bins: int,
) -> None:
    """equi_width preserves total_count."""
    h = equi_width(values, n_bins=n_bins)
    assert h.total_count == len(values)
    assert sum(b.count for b in h.bins) == len(values)


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=200,
    ),
    n_bins=st.integers(min_value=2, max_value=20),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_equi_depth_total_preserved(
    values: list[float],
    n_bins: int,
) -> None:
    """equi_depth preserves total_count."""
    h = equi_depth(values, n_bins=n_bins)
    assert h.total_count == len(values)
    assert sum(b.count for b in h.bins) == len(values)


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=200,
    ),
    n_bins=st.integers(min_value=2, max_value=20),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property_maxdiff_total_preserved(
    values: list[float],
    n_bins: int,
) -> None:
    h = maxdiff(values, n_bins=n_bins)
    assert h.total_count == len(values)


@given(
    base_values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
    new_values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_reproject_preserves_count(
    base_values: list[float],
    new_values: list[float],
) -> None:
    """Reprojection always produces a histogram with total_count == n_values."""
    template = equi_width(base_values, n_bins=5)
    out = reproject(new_values, template)
    assert out.total_count == len(new_values)
    assert out.n_bins == template.n_bins


# ---------- Categorical ------------------------------------------------------


@given(
    values=st.lists(
        st.text(alphabet="abcde", min_size=1, max_size=3),
        min_size=1,
        max_size=200,
    ),
    k=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=20)
def test_property_top_k_returns_at_most_k(
    values: list[str],
    k: int,
) -> None:
    out = top_k(values, k=k)
    assert len(out) <= k


@given(
    values=st.lists(
        st.text(alphabet="abcde", min_size=1, max_size=3),
        min_size=1,
        max_size=200,
        unique=True,
    ),
)
@settings(max_examples=20)
def test_property_cardinality_at_most_distinct(values: list[str]) -> None:
    """Cardinality never exceeds the number of distinct inputs."""
    count, _ = cardinality(values, cap=1_000)
    assert count <= len(values)


@given(
    values=st.lists(
        st.text(alphabet="abc", min_size=1, max_size=2),
        min_size=10,
        max_size=200,
    ),
)
@settings(max_examples=15)
def test_property_spacesaving_n_seen_matches(values: list[str]) -> None:
    """SpaceSaving.n_seen == # of calls to add()."""
    ss = SpaceSaving(k=3)
    for v in values:
        ss.add(v)
    assert ss.n_seen == len(values)


# ---------- collect_profile --------------------------------------------------


@given(
    values=st.lists(
        st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=100,
    ),
)
@settings(max_examples=15)
def test_property_numeric_profile_min_max_consistent(values: list[float]) -> None:
    """profile.numeric.min/max match min/max of input."""
    p = collect_profile("x", [str(v) for v in values], kind=ColumnKind.NUMERIC)
    assert p.numeric is not None
    assert p.numeric.min == min(values)
    assert p.numeric.max == max(values)


@given(
    n_a=st.integers(min_value=1, max_value=20),
    n_b=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=15)
def test_property_categorical_profile_top_k_counts_sum_le_total(
    n_a: int,
    n_b: int,
) -> None:
    """Top-K counts sum to <= total non-null count (since K may < cardinality)."""
    values = (["A"] * n_a) + (["B"] * n_b)
    p = collect_profile("c", values, kind=ColumnKind.CATEGORICAL)
    total = sum(t.count for t in p.top_k)
    assert total <= p.n_non_null


# ---------- PSI properties ---------------------------------------------------


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=100,
    ),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_psi_self_zero(values: list[float]) -> None:
    """PSI of a profile against itself is 0."""
    p = collect_profile("x", [str(v) for v in values], kind=ColumnKind.NUMERIC)
    assert abs(psi(p, p)) < 1e-9


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=80,
    ),
    shift=st.floats(min_value=0.1, max_value=1000),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_psi_non_negative(
    values: list[float],
    shift: float,
) -> None:
    """PSI is always >= 0."""
    baseline = collect_profile(
        "x",
        [str(v) for v in values],
        kind=ColumnKind.NUMERIC,
    )
    assert baseline.histogram is not None
    shifted_values = [v + shift for v in values]
    shifted_hist = reproject(shifted_values, baseline.histogram)
    compared = replace(
        baseline,
        n_rows=len(shifted_values),
        n_non_null=len(shifted_values),
        histogram=shifted_hist,
    )
    score = psi(baseline, compared)
    assert score >= 0
