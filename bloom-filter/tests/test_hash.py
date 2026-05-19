"""Hash family: determinism, independence, range."""

from __future__ import annotations

import pytest

from bloom.hash import hash64, positions


def test_hash64_deterministic() -> None:
    assert hash64("hello") == hash64("hello")


def test_hash64_different_seeds_diverge() -> None:
    assert hash64("hello", seed=0) != hash64("hello", seed=1)


def test_hash64_handles_str_bytes_int_float() -> None:
    # All variants should produce a 64-bit-bounded integer.
    for v in ("a", b"a", 42, 3.14):
        h = hash64(v)
        assert 0 <= h < (1 << 64)


def test_hash64_bytes_and_str_diverge() -> None:
    """The same byte content as str vs bytes hashes the same (UTF-8 encode).

    Strings are encoded to UTF-8 before hashing, so 'a' (str) and b'a'
    produce the same digest. Document the chosen behaviour.
    """
    assert hash64("a") == hash64(b"a")


def test_positions_count() -> None:
    p = positions("x", n_hashes=5, size_bits=1024)
    assert len(p) == 5


def test_positions_in_range() -> None:
    p = positions("x", n_hashes=10, size_bits=100)
    assert all(0 <= i < 100 for i in p)


def test_positions_deterministic() -> None:
    assert positions("x", 7, 1024) == positions("x", 7, 1024)


def test_positions_rejects_zero_hashes() -> None:
    with pytest.raises(ValueError, match="n_hashes"):
        positions("x", 0, 1024)


def test_positions_rejects_zero_size() -> None:
    with pytest.raises(ValueError, match="size_bits"):
        positions("x", 3, 0)


def test_positions_diverge_for_different_values() -> None:
    """Two different values should not produce identical position lists."""
    assert positions("alpha", 7, 4096) != positions("beta", 7, 4096)
