"""Tests for backfill schema utilities."""

from __future__ import annotations

import datetime

import pytest

from backfill.schema import Partition, PartitionState, date_range


class TestDateRange:
    def test_single_day(self) -> None:
        d = datetime.date(2025, 1, 1)
        assert date_range(d, d) == [d]

    def test_one_week(self) -> None:
        start = datetime.date(2025, 1, 1)
        end = datetime.date(2025, 1, 7)
        result = date_range(start, end)
        assert len(result) == 7
        assert result[0] == start
        assert result[-1] == end

    def test_step_days(self) -> None:
        start = datetime.date(2025, 1, 1)
        end = datetime.date(2025, 1, 15)
        result = date_range(start, end, step_days=7)
        assert result == [
            datetime.date(2025, 1, 1),
            datetime.date(2025, 1, 8),
            datetime.date(2025, 1, 15),
        ]

    def test_invalid_step_raises(self) -> None:
        with pytest.raises(ValueError):
            date_range(datetime.date(2025, 1, 1), datetime.date(2025, 1, 7), step_days=0)


class TestPartition:
    def test_partition_key(self) -> None:
        p = Partition(partition_date=datetime.date(2025, 6, 15))
        assert p.partition_key() == "2025-06-15"

    def test_to_dict_roundtrip(self) -> None:
        p = Partition(
            partition_date=datetime.date(2025, 3, 1),
            state=PartitionState.DONE,
            attempts=2,
            error_msg="",
            priority=5,
        )
        d = p.to_dict()
        restored = Partition.from_dict(d)
        assert restored.partition_date == p.partition_date
        assert restored.state == p.state
        assert restored.attempts == p.attempts
        assert restored.priority == p.priority


class TestPropertyIO:
    def test_all_states_serialisable(self) -> None:
        for state in PartitionState:
            p = Partition(partition_date=datetime.date(2025, 1, 1), state=state)
            d = p.to_dict()
            r = Partition.from_dict(d)
            assert r.state == state
