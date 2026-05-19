"""Sizing helpers: optimal m, k, and FPR estimation."""

from __future__ import annotations

import math

import pytest

from bloom.sizing import (
    bits_per_item,
    estimate_fpr,
    estimate_fpr_from_fill,
    optimal_n_hashes,
    optimal_size_bits,
)

# ---------- optimal_size_bits -----------------------------------------------


def test_size_one_percent_fpr_per_1k() -> None:
    """1% FPR ≈ 9.6 bits/item — published textbook constant."""
    m = optimal_size_bits(1_000, 0.01)
    assert 9_500 <= m <= 9_700


def test_size_tighter_fpr_costs_more_bits() -> None:
    m_loose = optimal_size_bits(1_000, 0.05)
    m_tight = optimal_size_bits(1_000, 0.001)
    assert m_tight > m_loose


def test_size_scales_linearly_with_capacity() -> None:
    m_1k = optimal_size_bits(1_000, 0.01)
    m_10k = optimal_size_bits(10_000, 0.01)
    # 10× capacity → roughly 10× bits.
    assert 9 * m_1k <= m_10k <= 11 * m_1k


def test_size_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        optimal_size_bits(0, 0.01)


def test_size_rejects_bad_fpr() -> None:
    with pytest.raises(ValueError, match="target_fpr"):
        optimal_size_bits(100, 0.0)
    with pytest.raises(ValueError, match="target_fpr"):
        optimal_size_bits(100, 1.0)


# ---------- optimal_n_hashes ------------------------------------------------


def test_optimal_hashes_for_one_percent() -> None:
    """At 1% FPR optimal k ≈ 7 (textbook)."""
    m = optimal_size_bits(1_000, 0.01)
    k = optimal_n_hashes(m, 1_000)
    assert 6 <= k <= 8


def test_optimal_hashes_at_least_one() -> None:
    """Even degenerate m/n must produce k ≥ 1."""
    assert optimal_n_hashes(2, 1_000_000) == 1


def test_optimal_hashes_rejects_zero() -> None:
    with pytest.raises(ValueError, match="size_bits"):
        optimal_n_hashes(0, 100)
    with pytest.raises(ValueError, match="capacity"):
        optimal_n_hashes(100, 0)


# ---------- estimate_fpr ----------------------------------------------------


def test_estimate_fpr_zero_items_is_zero() -> None:
    assert estimate_fpr(1024, 7, 0) == 0.0


def test_estimate_fpr_matches_target_at_capacity() -> None:
    """When the filter holds exactly capacity items, FPR ≈ target."""
    capacity = 1_000
    target = 0.01
    m = optimal_size_bits(capacity, target)
    k = optimal_n_hashes(m, capacity)
    actual = estimate_fpr(m, k, capacity)
    # Within 10% of target.
    assert 0.009 <= actual <= 0.011


def test_estimate_fpr_monotonic_with_items() -> None:
    """FPR strictly increases as we insert more items."""
    m, k = 4096, 5
    fprs = [estimate_fpr(m, k, n) for n in (100, 500, 1000, 5000)]
    assert fprs == sorted(fprs)


def test_estimate_fpr_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match="size_bits"):
        estimate_fpr(0, 3, 100)
    with pytest.raises(ValueError, match="n_hashes"):
        estimate_fpr(100, 0, 100)
    with pytest.raises(ValueError, match="n_items"):
        estimate_fpr(100, 3, -1)


# ---------- estimate_fpr_from_fill ------------------------------------------


def test_estimate_fpr_from_fill_basic() -> None:
    # fill 0.5, k=7 → 0.5^7 ≈ 0.0078
    assert math.isclose(estimate_fpr_from_fill(0.5, 7), 0.5**7)


def test_estimate_fpr_from_fill_zero() -> None:
    assert estimate_fpr_from_fill(0.0, 7) == 0.0


def test_estimate_fpr_from_fill_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="fill_ratio"):
        estimate_fpr_from_fill(1.5, 7)


# ---------- bits_per_item ---------------------------------------------------


def test_bits_per_item_one_percent() -> None:
    """1% FPR ≈ 9.585 bits/item."""
    assert math.isclose(bits_per_item(0.01), 9.585, abs_tol=0.01)


def test_bits_per_item_tightens_with_lower_fpr() -> None:
    assert bits_per_item(0.001) > bits_per_item(0.01)


def test_bits_per_item_rejects_bad_fpr() -> None:
    with pytest.raises(ValueError, match="target_fpr"):
        bits_per_item(0.0)
