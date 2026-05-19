"""Schema invariants for BloomFilter / BuildableBloom / CountingBloom / ScalableBloom."""

from __future__ import annotations

import pytest

from bloom.schema import (
    BloomFilter,
    BuildableBloom,
    CountingBloom,
    ScalableBloom,
)

# ---------- BloomFilter -----------------------------------------------------


def test_bloom_filter_basic() -> None:
    bf = BloomFilter(size_bits=64, n_hashes=3, n_items=0, bits=0)
    assert bf.size_bits == 64
    assert bf.fill_ratio == 0.0
    assert not bf.is_saturated


def test_bloom_filter_fill_ratio() -> None:
    """One bit set in 8-bit filter → fill 1/8."""
    bf = BloomFilter(size_bits=8, n_hashes=2, n_items=1, bits=0b00010000)
    assert bf.fill_ratio == 1 / 8


def test_bloom_filter_saturated() -> None:
    bf = BloomFilter(size_bits=8, n_hashes=2, n_items=4, bits=0b11111000)
    assert bf.is_saturated


def test_bloom_filter_rejects_zero_size() -> None:
    with pytest.raises(ValueError, match="size_bits"):
        BloomFilter(size_bits=0, n_hashes=3, n_items=0, bits=0)


def test_bloom_filter_rejects_zero_hashes() -> None:
    with pytest.raises(ValueError, match="n_hashes"):
        BloomFilter(size_bits=64, n_hashes=0, n_items=0, bits=0)


def test_bloom_filter_rejects_negative_items() -> None:
    with pytest.raises(ValueError, match="n_items"):
        BloomFilter(size_bits=64, n_hashes=3, n_items=-1, bits=0)


def test_bloom_filter_rejects_oversized_bits() -> None:
    """bits with more significant bits than size_bits is invalid."""
    with pytest.raises(ValueError, match="exceeds size_bits"):
        BloomFilter(size_bits=4, n_hashes=2, n_items=1, bits=0xFFFF)


# ---------- BuildableBloom --------------------------------------------------


def test_buildable_basic() -> None:
    bf = BuildableBloom(
        size_bits=64,
        n_hashes=3,
        capacity=10,
        target_fpr=0.01,
        _bits=bytearray(8),
    )
    assert bf.fill_ratio == 0.0
    assert bf.n_items == 0


def test_buildable_rejects_bad_target_fpr() -> None:
    with pytest.raises(ValueError, match="target_fpr"):
        BuildableBloom(
            size_bits=64,
            n_hashes=3,
            capacity=10,
            target_fpr=0.0,
            _bits=bytearray(8),
        )
    with pytest.raises(ValueError, match="target_fpr"):
        BuildableBloom(
            size_bits=64,
            n_hashes=3,
            capacity=10,
            target_fpr=1.0,
            _bits=bytearray(8),
        )


def test_buildable_rejects_bits_length_mismatch() -> None:
    with pytest.raises(ValueError, match="_bits length"):
        BuildableBloom(
            size_bits=64,
            n_hashes=3,
            capacity=10,
            target_fpr=0.01,
            _bits=bytearray(4),
        )


# ---------- CountingBloom ---------------------------------------------------


def test_counting_basic() -> None:
    cb = CountingBloom(
        size_buckets=64,
        n_hashes=3,
        capacity=10,
        target_fpr=0.01,
        _counters=bytearray(64),
    )
    assert cb.n_items == 0


def test_counting_rejects_bucket_length_mismatch() -> None:
    with pytest.raises(ValueError, match="_counters length"):
        CountingBloom(
            size_buckets=64,
            n_hashes=3,
            capacity=10,
            target_fpr=0.01,
            _counters=bytearray(32),
        )


# ---------- ScalableBloom ---------------------------------------------------


def test_scalable_basic() -> None:
    sb = ScalableBloom(
        initial_capacity=100,
        target_fpr=0.01,
        growth_factor=2,
        tightening_ratio=0.5,
    )
    assert sb.n_items == 0
    assert sb.n_slices == 0


def test_scalable_rejects_bad_growth() -> None:
    with pytest.raises(ValueError, match="growth_factor"):
        ScalableBloom(
            initial_capacity=100,
            target_fpr=0.01,
            growth_factor=1,
            tightening_ratio=0.5,
        )


def test_scalable_rejects_bad_tightening() -> None:
    with pytest.raises(ValueError, match="tightening_ratio"):
        ScalableBloom(
            initial_capacity=100,
            target_fpr=0.01,
            growth_factor=2,
            tightening_ratio=1.0,
        )


def test_scalable_rejects_bad_capacity() -> None:
    with pytest.raises(ValueError, match="initial_capacity"):
        ScalableBloom(
            initial_capacity=0,
            target_fpr=0.01,
            growth_factor=2,
            tightening_ratio=0.5,
        )
