"""BloomFilter behavioral tests."""

from __future__ import annotations

import pytest

from bloomdedup.bloom import BloomFilter
from bloomdedup.schema import BloomParams


def test_add_returns_false_first_time() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    assert bf.add("alpha") is False
    assert "alpha" in bf


def test_add_returns_true_second_time() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    bf.add("alpha")
    assert bf.add("alpha") is True


def test_no_false_negatives() -> None:
    """Anything we've added must report as present."""
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    items = [f"k{i:05d}" for i in range(500)]
    for it in items:
        bf.add(it)
    for it in items:
        assert it in bf


def test_few_false_positives_under_capacity() -> None:
    """At-load FPR should be close to target."""
    cap = 1000
    bf = BloomFilter(BloomParams.for_capacity(cap, fpr=0.01))
    for i in range(cap):
        bf.add(f"in-{i:05d}")
    fp = sum(1 for i in range(10_000) if f"out-{i:05d}" in bf)
    rate = fp / 10_000
    # Should be roughly ≤ 2% (target 1%, give it leeway for randomness).
    assert rate < 0.03


def test_update_bulk() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    bf.update([f"k{i}" for i in range(100)])
    assert "k50" in bf
    assert bf.n_added == 100


def test_contains_rejects_non_string() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    bf.add("x")
    assert (1 not in bf) is True
    assert (None not in bf) is True


def test_fill_ratio_grows_with_inserts() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    initial = bf.fill_ratio
    assert initial == 0.0
    bf.update([f"k{i}" for i in range(100)])
    mid = bf.fill_ratio
    assert 0.0 < mid < 1.0


def test_serialise_roundtrip() -> None:
    params = BloomParams.for_capacity(1000, fpr=0.01)
    bf = BloomFilter(params)
    bf.update([f"k{i}" for i in range(100)])
    data = bf.to_bytes()
    bf2 = BloomFilter.from_bytes(params, data)
    for i in range(100):
        assert f"k{i}" in bf2


def test_serialise_rejects_wrong_length() -> None:
    params = BloomParams.for_capacity(1000, fpr=0.01)
    with pytest.raises(ValueError):
        BloomFilter.from_bytes(params, b"\x00" * (params.m_bytes - 1))


def test_unicode_keys() -> None:
    bf = BloomFilter(BloomParams.for_capacity(1000, fpr=0.01))
    bf.add("café")
    bf.add("ngôn ngữ")
    assert "café" in bf
    assert "ngôn ngữ" in bf
    assert "coffee" not in bf  # could be FP but with separate strings unlikely
