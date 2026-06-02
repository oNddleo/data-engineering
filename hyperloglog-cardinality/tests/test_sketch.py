"""HyperLogLog accuracy + merge + stats."""

from __future__ import annotations

import pytest

from hllpp.sketch import add, estimate, merge, new_sketch, stats


def _build(values: list[str], precision: int = 14) -> object:
    """Helper: build a sketch from a list of values."""
    s = new_sketch(precision=precision)
    for v in values:
        add(s, v)
    return s


# ---------- estimate accuracy ------------------------------------------------


def test_empty_sketch_estimates_zero():
    s = new_sketch()
    assert estimate(s) == 0


def test_one_value_estimates_one():
    s = new_sketch()
    add(s, "hello")
    assert estimate(s) == 1


def test_duplicates_dont_inflate_estimate():
    """100 distinct values, repeated 10× each → estimate ≈ 100."""
    s = new_sketch()
    for _ in range(10):
        for i in range(100):
            add(s, f"v_{i}")
    e = estimate(s)
    assert 90 <= e <= 110


def test_estimate_within_2_pct_for_10k():
    """10 000 distinct values, p=14 → estimate within ±2% (standard error ≈ 0.8%)."""
    values = [f"v_{i}" for i in range(10_000)]
    s = _build(values, precision=14)
    e = estimate(s)
    assert 9_800 <= e <= 10_200, f"estimate {e} out of 10000 ±2%"


def test_estimate_within_5_pct_for_100k():
    """100 000 distinct, p=12 → within ±5% (std error ~1.6%)."""
    values = [f"v_{i}" for i in range(100_000)]
    s = _build(values, precision=12)
    e = estimate(s)
    assert 95_000 <= e <= 105_000, f"estimate {e} out of 100000 ±5%"


def test_estimate_uses_linear_counting_for_small_n():
    """Very small cardinalities should be near-exact (linear counting)."""
    s = new_sketch()
    for i in range(5):
        add(s, f"v_{i}")
    e = estimate(s)
    assert e == 5


def test_estimate_low_precision_lower_accuracy():
    """p=8 (m=256) → error ~6.5%; estimate 1000 distinct within ±20%."""
    s = new_sketch(precision=8)
    for i in range(1000):
        add(s, f"v_{i}")
    e = estimate(s)
    assert 800 <= e <= 1200


# ---------- merge ------------------------------------------------------------


def test_merge_disjoint_streams_unions():
    """Merging two disjoint 5k streams → estimate ≈ 10k."""
    a = _build([f"a_{i}" for i in range(5_000)])
    b = _build([f"b_{i}" for i in range(5_000)])
    merged = merge(a, b)
    e = estimate(merged)
    assert 9_700 <= e <= 10_300


def test_merge_overlapping_streams_dedup():
    """Merging two streams of identical 5k values → estimate ≈ 5k."""
    a = _build([f"v_{i}" for i in range(5_000)])
    b = _build([f"v_{i}" for i in range(5_000)])
    merged = merge(a, b)
    e = estimate(merged)
    assert 4_800 <= e <= 5_200


def test_merge_register_max():
    """Merged sketch's register == max of inputs' registers."""
    a = new_sketch(precision=4)
    b = new_sketch(precision=4)
    a.registers[0] = 7
    a.registers[5] = 2
    b.registers[0] = 3
    b.registers[5] = 9
    merged = merge(a, b)
    assert merged.registers[0] == 7
    assert merged.registers[5] == 9


def test_merge_rejects_different_precisions():
    a = new_sketch(precision=10)
    b = new_sketch(precision=12)
    with pytest.raises(ValueError, match="same precision"):
        merge(a, b)


def test_merge_empty_returns_empty():
    out = merge()
    assert out.n_zero_registers() == out.m
    assert estimate(out) == 0


def test_merge_single_sketch_returns_copy():
    a = _build([f"v_{i}" for i in range(100)])
    merged = merge(a)
    assert estimate(merged) == estimate(a)


# ---------- stats ------------------------------------------------------------


def test_stats_for_empty_sketch():
    s = new_sketch(precision=14)
    summary = stats(s)
    assert summary.estimated_cardinality == 0
    assert summary.n_zero_registers == 16384
    assert summary.max_register == 0


def test_stats_for_filled_sketch():
    s = _build([f"v_{i}" for i in range(1_000)])
    summary = stats(s)
    assert summary.estimated_cardinality > 0
    assert summary.n_zero_registers < summary.m
    assert summary.max_register > 0


def test_stats_standard_error_for_p14():
    s = new_sketch(precision=14)
    summary = stats(s)
    # Standard error: 1.04 / sqrt(16384) * 100 ≈ 0.8125%
    assert abs(summary.standard_error_pct - 0.8125) < 0.001


def test_stats_standard_error_for_p4():
    s = new_sketch(precision=4)
    summary = stats(s)
    # 1.04 / sqrt(16) * 100 ≈ 26%
    assert abs(summary.standard_error_pct - 26.0) < 0.5
