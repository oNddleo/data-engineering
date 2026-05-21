"""BloomParams sizing."""

from __future__ import annotations

import pytest

from bloomdedup.schema import BloomParams


def test_basic_sizing() -> None:
    p = BloomParams.for_capacity(1000, fpr=0.01)
    # ~9.6 bits/item is the textbook number for 1% FPR.
    bits_per_item = p.m_bits / p.capacity
    assert 9.0 <= bits_per_item <= 11.0
    assert p.k_hashes >= 5


def test_byte_aligned_size() -> None:
    """m_bits must be byte-aligned for whole-byte storage."""
    p = BloomParams.for_capacity(1000, fpr=0.01)
    assert p.m_bits % 8 == 0
    assert p.m_bytes * 8 == p.m_bits


def test_tighter_fpr_more_bits() -> None:
    p_loose = BloomParams.for_capacity(1000, fpr=0.1)
    p_tight = BloomParams.for_capacity(1000, fpr=0.001)
    assert p_tight.m_bits > p_loose.m_bits


def test_larger_capacity_more_bits() -> None:
    p_small = BloomParams.for_capacity(100, fpr=0.01)
    p_large = BloomParams.for_capacity(10_000, fpr=0.01)
    assert p_large.m_bits > p_small.m_bits


@pytest.mark.parametrize("bad_cap", [0, -1])
def test_capacity_validation(bad_cap: int) -> None:
    with pytest.raises(ValueError):
        BloomParams.for_capacity(bad_cap, fpr=0.01)


@pytest.mark.parametrize("bad_fpr", [-0.1, 0.0, 1.0, 1.5])
def test_fpr_validation(bad_fpr: float) -> None:
    with pytest.raises(ValueError):
        BloomParams.for_capacity(100, fpr=bad_fpr)


def test_k_at_least_one() -> None:
    """Even degenerate sizing produces k >= 1."""
    p = BloomParams.for_capacity(1, fpr=0.5)
    assert p.k_hashes >= 1
