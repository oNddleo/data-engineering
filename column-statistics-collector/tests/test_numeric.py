"""Welford accumulator + numeric_stats."""

from __future__ import annotations

import statistics

from colstats.numeric import WelfordAccumulator, numeric_stats


def test_welford_empty_zero():
    w = WelfordAccumulator()
    assert w.n == 0
    assert w.mean == 0.0
    assert w.variance == 0.0
    assert w.std == 0.0


def test_welford_one_value_variance_zero():
    """A single observation has no variance (n < 2)."""
    w = WelfordAccumulator()
    w.add(42.0)
    assert w.mean == 42.0
    assert w.variance == 0.0


def test_welford_matches_stdlib_std():
    """Welford std matches statistics.stdev across a range of inputs."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    w = WelfordAccumulator()
    for v in data:
        w.add(v)
    expected = statistics.stdev(data)
    assert abs(w.std - expected) < 1e-9


def test_welford_numerically_stable():
    """Welford should not catastrophically cancel on shifted data."""
    # Reference values shifted by 1e9 — naive sum-of-squares would lose precision.
    data = [1e9 + i for i in range(100)]
    w = WelfordAccumulator()
    for v in data:
        w.add(v)
    naive = [v for v in data]
    expected = statistics.stdev(naive)
    assert abs(w.std - expected) < 1e-6


# ---------- numeric_stats ----------------------------------------------------


def test_numeric_stats_basic():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    ns = numeric_stats(data)
    assert ns.min == 1.0
    assert ns.max == 5.0
    assert abs(ns.mean - 3.0) < 1e-9
    assert ns.p50 == 3.0


def test_numeric_stats_percentiles():
    data = [float(i) for i in range(1, 101)]
    ns = numeric_stats(data)
    # nearest-rank p25 of 1..100 = 25
    assert ns.p25 == 25.0
    assert ns.p50 == 50.0
    assert ns.p75 == 75.0
    assert ns.p95 == 95.0
    assert ns.p99 == 99.0


def test_numeric_stats_empty():
    ns = numeric_stats([])
    assert ns.min == 0.0
    assert ns.max == 0.0
    assert ns.std == 0.0


def test_numeric_stats_single_value():
    ns = numeric_stats([42.0])
    assert ns.min == ns.max == 42.0
    assert ns.std == 0.0
    assert ns.p99 == 42.0
