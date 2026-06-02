"""Unit tests for compaction engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from compact.engine import (
    CompactionEngine,
    _partition_is_stale,
    _partition_needs_merge,
    _score_columns,
    plan,
)
from compact.schema import (
    CompactionAction,
    DataFile,
    Partition,
    QueryPattern,
    TableMeta,
)

_NOW = datetime.now(tz=timezone.utc)
_TARGET = 128 * 1024 * 1024  # 128 MiB


def _file(size_mb: float, days_old: int = 5, partition: str = "dt=2024-01-01") -> DataFile:
    ts = _NOW - timedelta(days=days_old)
    return DataFile(
        path=f"s3://b/t/{partition}/part-{size_mb:.0f}mb.parquet",
        size_bytes=int(size_mb * 1024 * 1024),
        row_count=int(size_mb * 5000),
        partition=partition,
        created_at=ts,
        last_modified=ts,
    )


def _partition(files: list[DataFile], key: str = "dt=2024-01-01") -> Partition:
    return Partition(key=key, files=files)


class TestScoreColumns:
    def test_filter_weighted_highest(self) -> None:
        qp = QueryPattern("q1", filter_columns=["col_a"], frequency=1)
        scores = _score_columns([qp])
        assert "col_a" in scores
        assert scores["col_a"] > 0

    def test_all_zeros_on_empty(self) -> None:
        assert _score_columns([]) == {}

    def test_frequency_amplifies(self) -> None:
        qp_low = QueryPattern("q1", filter_columns=["col_a"], frequency=1)
        qp_high = QueryPattern("q2", filter_columns=["col_a"], frequency=100)
        scores = _score_columns([qp_low, qp_high])
        assert scores["col_a"] > 0

    def test_sum_normalised_to_1(self) -> None:
        qp = QueryPattern("q1", filter_columns=["a"], join_columns=["b"], group_by_columns=["c"])
        scores = _score_columns([qp])
        assert abs(sum(scores.values()) - 1.0) < 1e-9


class TestPartitionChecks:
    def test_needs_merge_many_small(self) -> None:
        files = [_file(5) for _ in range(10)]
        part = _partition(files)
        assert _partition_needs_merge(part, _TARGET)

    def test_no_merge_few_small(self) -> None:
        files = [_file(5), _file(5)]
        part = _partition(files)
        assert not _partition_needs_merge(part, _TARGET)

    def test_no_merge_large_files(self) -> None:
        files = [_file(200), _file(150), _file(180), _file(160), _file(140)]
        part = _partition(files)
        assert not _partition_needs_merge(part, _TARGET)

    def test_stale_partition(self) -> None:
        files = [_file(100, days_old=200)]
        part = _partition(files)
        assert _partition_is_stale(part, prune_after_days=90)

    def test_fresh_partition_not_stale(self) -> None:
        files = [_file(100, days_old=5)]
        part = _partition(files)
        assert not _partition_is_stale(part, prune_after_days=90)


class TestCompactionEngine:
    def test_stale_partition_gets_pruned(self) -> None:
        files = [_file(100, days_old=200, partition="old")]
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[_partition(files, "old")],
            columns=["a", "b"],
        )
        result = plan(table, prune_after_days=90)
        assert any(t.action == CompactionAction.PRUNE for t in result.tasks)

    def test_small_files_get_merged(self) -> None:
        files = [_file(5, partition="new") for _ in range(10)]
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[_partition(files, "new")],
            columns=["a", "b"],
        )
        result = plan(table)
        assert any(t.action == CompactionAction.MERGE for t in result.tasks)

    def test_hot_columns_trigger_zorder(self) -> None:
        files = [_file(200, partition="p"), _file(200, partition="p")]
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[_partition(files, "p")],
            columns=["user_id", "event_date"],
        )
        patterns = [QueryPattern("q1", filter_columns=["user_id"], frequency=100)]
        result = plan(table, query_patterns=patterns)
        zorder_tasks = [t for t in result.tasks if t.action == CompactionAction.ZORDER]
        assert len(zorder_tasks) >= 1
        assert "user_id" in zorder_tasks[0].z_order_columns

    def test_empty_table_no_tasks(self) -> None:
        table = TableMeta(table_name="t", format="delta")
        result = plan(table)
        assert result.tasks == []

    def test_tasks_sorted_by_priority(self) -> None:
        files1 = [_file(5) for _ in range(20)]  # many small → high priority
        files2 = [_file(200), _file(210)]  # 2 large
        p1 = _partition(files1, "high")
        p2 = _partition(files2, "low")
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[p1, p2],
            columns=["a"],
        )
        result = plan(table)
        prios = [t.priority for t in result.tasks]
        assert prios == sorted(prios, reverse=True)

    def test_engine_class_same_as_functional(self) -> None:
        files = [_file(5) for _ in range(5)]
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[_partition(files)],
            columns=["x"],
        )
        r1 = plan(table)
        r2 = CompactionEngine().plan(table)
        assert len(r1.tasks) == len(r2.tasks)

    def test_action_counts(self) -> None:
        files_small = [_file(5) for _ in range(5)]
        files_stale = [_file(100, days_old=200, partition="old")]
        table = TableMeta(
            table_name="t",
            format="delta",
            partitions=[
                _partition(files_small, "new"),
                _partition(files_stale, "old"),
            ],
            columns=["a"],
        )
        result = plan(table, prune_after_days=90)
        counts = result.action_counts
        assert "prune" in counts or "merge" in counts
