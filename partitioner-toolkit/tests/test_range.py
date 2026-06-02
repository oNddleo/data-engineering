"""RangePartitioner."""

from __future__ import annotations

import pytest

from partitioner.range_part import RangePartitioner


def test_basic_ranges() -> None:
    """boundaries=[10,20,30] → 4 partitions, half-open at right."""
    p = RangePartitioner([10, 20, 30])
    assert p.partition_for(5) == 0
    assert p.partition_for(10) == 1  # [10,20) — boundary goes right
    assert p.partition_for(15) == 1
    assert p.partition_for(20) == 2
    assert p.partition_for(29) == 2
    assert p.partition_for(30) == 3
    assert p.partition_for(100) == 3


def test_n_partitions() -> None:
    assert RangePartitioner([10, 20, 30]).n_partitions == 4
    assert RangePartitioner([]).n_partitions == 1


def test_no_boundaries() -> None:
    """Empty boundary list = single partition for everything."""
    p = RangePartitioner([])
    assert p.partition_for(-1) == 0
    assert p.partition_for(0) == 0
    assert p.partition_for(1_000_000) == 0


def test_rejects_non_ascending() -> None:
    with pytest.raises(ValueError):
        RangePartitioner([10, 10, 20])
    with pytest.raises(ValueError):
        RangePartitioner([20, 10])


def test_boundaries_property_returns_copy() -> None:
    """Mutating the returned list shouldn't affect the partitioner."""
    p = RangePartitioner([10, 20])
    b = p.boundaries
    b.append(999)
    assert p.boundaries == [10, 20]
