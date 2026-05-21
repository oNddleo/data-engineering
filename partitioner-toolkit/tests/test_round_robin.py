"""RoundRobinPartitioner."""

from __future__ import annotations

import pytest

from partitioner.round_robin import RoundRobinPartitioner


def test_cycles() -> None:
    rr = RoundRobinPartitioner(3)
    assert [rr.next_partition() for _ in range(6)] == [0, 1, 2, 0, 1, 2]


def test_reset() -> None:
    rr = RoundRobinPartitioner(3)
    rr.next_partition()
    rr.next_partition()
    rr.reset()
    assert rr.next_partition() == 0


def test_single_partition() -> None:
    rr = RoundRobinPartitioner(1)
    assert all(rr.next_partition() == 0 for _ in range(10))


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_bad_count(bad: int) -> None:
    with pytest.raises(ValueError):
        RoundRobinPartitioner(bad)
