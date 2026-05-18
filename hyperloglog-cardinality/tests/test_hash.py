"""hash64 + leading_zeros_64."""

from __future__ import annotations

from hllpp.hash import hash64, leading_zeros_64

# ---------- hash64 -----------------------------------------------------------


def test_hash64_deterministic_str():
    """Same string → same hash across calls."""
    assert hash64("hello") == hash64("hello")


def test_hash64_deterministic_bytes():
    assert hash64(b"hello") == hash64(b"hello")


def test_hash64_different_inputs_differ():
    assert hash64("hello") != hash64("world")


def test_hash64_str_bytes_equivalent():
    """str input is utf-8 encoded → same hash as bytes."""
    assert hash64("hello") == hash64(b"hello")


def test_hash64_int_input():
    assert hash64(42) == hash64(42)
    assert hash64(42) != hash64(43)


def test_hash64_returns_uint64_range():
    """Hashes are in [0, 2^64)."""
    for v in ("a", "b", "c", "hello world"):
        h = hash64(v)
        assert 0 <= h < (1 << 64)


def test_hash64_uniform_distribution_smoke():
    """A million-input batch should fairly evenly populate top-p bits."""
    p = 8
    buckets = [0] * (1 << p)
    for i in range(50_000):
        h = hash64(f"v_{i}")
        idx = h >> (64 - p)
        buckets[idx] += 1
    expected = 50_000 / (1 << p)
    # Each bucket should be within 25% of the expected mean
    for c in buckets:
        assert 0.5 * expected < c < 1.5 * expected, f"bucket count {c}"


# ---------- leading_zeros_64 -------------------------------------------------


def test_leading_zeros_x_zero():
    """x == 0 → max_zeros (the absolute ceiling)."""
    assert leading_zeros_64(0, max_zeros=50) == 50


def test_leading_zeros_top_bit_set():
    """Top bit of an N-bit field set → rho = 1."""
    # 60-bit field, top bit set
    width = 60
    x = 1 << (width - 1)
    assert leading_zeros_64(x, max_zeros=width + 1) == 1


def test_leading_zeros_bottom_bit_set():
    """Only bit-0 set in a 60-bit field → rho = 60."""
    assert leading_zeros_64(1, max_zeros=61) == 60


def test_leading_zeros_middle_bit():
    """5th-from-top bit set in a 60-bit field → rho = 5."""
    # 60-bit field; bit 55 (5th from top, 0-indexed) set
    width = 60
    x = 1 << (width - 5)
    assert leading_zeros_64(x, max_zeros=width + 1) == 5
