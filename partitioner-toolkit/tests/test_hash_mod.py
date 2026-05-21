"""HashModPartitioner."""

from __future__ import annotations

import pytest

from partitioner.hash_mod import HashModPartitioner


def test_basic_partition() -> None:
    p = HashModPartitioner(8)
    assert 0 <= p.partition_for("alpha") < 8


def test_stable_across_calls() -> None:
    p = HashModPartitioner(8)
    a = p.partition_for("alpha")
    b = p.partition_for("alpha")
    assert a == b


def test_stable_across_instances() -> None:
    """Same key + same partition count must yield same partition."""
    p1 = HashModPartitioner(16)
    p2 = HashModPartitioner(16)
    assert p1.partition_for("alpha") == p2.partition_for("alpha")


def test_distribution_roughly_uniform() -> None:
    p = HashModPartitioner(8)
    counts = [0] * 8
    for i in range(10_000):
        counts[p.partition_for(f"k{i}")] += 1
    # Expected mean 1250, allow ±20%.
    assert all(1000 <= c <= 1500 for c in counts)


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_bad_partition_count(bad: int) -> None:
    with pytest.raises(ValueError):
        HashModPartitioner(bad)


def test_n1_always_zero() -> None:
    p = HashModPartitioner(1)
    for i in range(100):
        assert p.partition_for(f"k{i}") == 0
