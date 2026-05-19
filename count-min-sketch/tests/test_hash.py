"""Hash family: hash64 + index_for."""

from __future__ import annotations

import pytest

from cms.hash import hash64, index_for


def test_hash64_deterministic():
    assert hash64("hello") == hash64("hello")


def test_hash64_seed_changes_output():
    """Different seeds produce different hashes (in general)."""
    seed0 = hash64("hello", seed=0)
    seed1 = hash64("hello", seed=1)
    seed2 = hash64("hello", seed=2)
    # Hash uniformity → near-zero probability all three equal.
    assert len({seed0, seed1, seed2}) > 1


def test_hash64_str_bytes_equivalent():
    assert hash64("hello") == hash64(b"hello")


def test_hash64_int_input():
    assert hash64(42, seed=3) == hash64(42, seed=3)


def test_hash64_in_uint64_range():
    for v in ("a", "b", "c", "very long input string"):
        h = hash64(v)
        assert 0 <= h < (1 << 64)


def test_index_for_in_bucket_range():
    """index_for returns a valid bucket index."""
    for seed in range(7):
        for v in ("a", "hello", "world"):
            idx = index_for(v, seed=seed, width=1024)
            assert 0 <= idx < 1024


def test_index_for_rejects_zero_width():
    with pytest.raises(ValueError, match="width"):
        index_for("x", seed=0, width=0)


def test_index_for_seed_changes_index():
    """Different seeds for the same value generally hit different buckets."""
    indices = {index_for("hello", seed=s, width=2719) for s in range(7)}
    # 7 hashes, uniform over 2719 buckets — distinct with high probability.
    assert len(indices) >= 6


def test_index_for_uniform_distribution_smoke():
    """Inserts spread across many buckets for a single seed."""
    width = 1024
    buckets = [0] * width
    for i in range(20_000):
        idx = index_for(f"v_{i}", seed=0, width=width)
        buckets[idx] += 1
    # Each bucket should be near the mean of ~20.
    nonzero = sum(1 for c in buckets if c > 0)
    assert nonzero > 900  # > 87% of buckets touched
