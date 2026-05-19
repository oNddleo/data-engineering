"""Scale function k(q): boundary values + size bound monotonicity."""

from __future__ import annotations

import math

import pytest

from tdigest.scale import k, max_combined_weight, q_from_k


def test_k_at_midpoint_is_zero() -> None:
    """k(0.5, δ) = δ/(2π) · asin(0) = 0."""
    assert math.isclose(k(0.5, 100.0), 0.0)


def test_k_at_zero() -> None:
    """k(0, δ) = δ/(2π) · asin(-1) = -δ/4."""
    expected = -100.0 / 4
    assert math.isclose(k(0.0, 100.0), expected)


def test_k_at_one() -> None:
    """k(1, δ) = δ/(2π) · asin(1) = δ/4."""
    expected = 100.0 / 4
    assert math.isclose(k(1.0, 100.0), expected)


def test_k_monotonic() -> None:
    """k(q) is strictly increasing in q."""
    samples = [k(q, 100.0) for q in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0)]
    assert samples == sorted(samples)


def test_k_proportional_to_compression() -> None:
    assert math.isclose(k(0.25, 200.0), 2 * k(0.25, 100.0))


def test_k_inverse_roundtrip() -> None:
    """q_from_k(k(q)) ≈ q for q in (0, 1)."""
    for q in (0.05, 0.25, 0.5, 0.75, 0.95):
        recovered = q_from_k(k(q, 100.0), 100.0)
        assert math.isclose(recovered, q, abs_tol=1e-9)


def test_k_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="q"):
        k(1.1, 100.0)
    with pytest.raises(ValueError, match="q"):
        k(-0.1, 100.0)


def test_k_rejects_low_compression() -> None:
    with pytest.raises(ValueError, match="compression"):
        k(0.5, 0.5)


# ---------- max_combined_weight --------------------------------------------


def test_size_bound_smaller_at_tails() -> None:
    """Centroids near q=0 or q=1 must have smaller max weight than at q=0.5."""
    total = 10_000.0
    tail = max_combined_weight(0.0, total, 100.0)
    mid = max_combined_weight(0.5, total, 100.0)
    assert tail < mid


def test_size_bound_is_nonnegative() -> None:
    for q in (0.0, 0.1, 0.5, 0.9, 1.0):
        assert max_combined_weight(q, 10_000.0, 100.0) >= 0


def test_size_bound_zero_total() -> None:
    assert max_combined_weight(0.0, 0.0, 100.0) == 0.0


def test_size_bound_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="q_left"):
        max_combined_weight(-0.1, 1_000.0, 100.0)


def test_size_bound_larger_compression_smaller_centroid() -> None:
    """Higher compression → tighter centroids → smaller per-centroid weight."""
    loose = max_combined_weight(0.5, 10_000.0, 50.0)
    tight = max_combined_weight(0.5, 10_000.0, 500.0)
    assert tight < loose
