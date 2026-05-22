"""Tests for JSONL I/O round-trip."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from compact.io_jsonl import (
    datafile_from_dict,
    datafile_to_dict,
    dump_tablemeta,
    load_tablemeta,
    plan_from_jsonl,
    plan_to_jsonl,
    tablemeta_from_dict,
    tablemeta_to_dict,
)
from compact.schema import (
    CompactionAction,
    CompactionPlan,
    CompactionTask,
    DataFile,
    TableMeta,
)
from compact.simulator import generate_table


def _sample_file() -> DataFile:
    now = datetime.now(tz=timezone.utc)
    return DataFile(
        path="s3://b/t/part-0001.parquet",
        size_bytes=50 * 1024 * 1024,
        row_count=250_000,
        partition="dt=2024-01-01",
        created_at=now,
        last_modified=now,
    )


class TestDataFileIO:
    def test_roundtrip_dict(self) -> None:
        f = _sample_file()
        d = datafile_to_dict(f)
        f2 = datafile_from_dict(d)
        assert f.path == f2.path
        assert f.size_bytes == f2.size_bytes
        assert f.row_count == f2.row_count

    def test_bad_type_raises(self) -> None:
        d: dict[str, object] = {
            "path": 123,  # wrong type
            "size_bytes": 1000,
            "row_count": 50,
            "partition": "p",
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_modified": "2024-01-01T00:00:00+00:00",
        }
        with pytest.raises(TypeError):
            datafile_from_dict(d)


class TestTableMetaIO:
    def test_roundtrip_dict(self) -> None:
        table = generate_table(n_partitions=3, seed=1)
        d = tablemeta_to_dict(table)
        table2 = tablemeta_from_dict(d)
        assert table.table_name == table2.table_name
        assert len(table.partitions) == len(table2.partitions)

    def test_roundtrip_file(self) -> None:
        table = generate_table(n_partitions=5, seed=2)
        buf = io.StringIO()
        dump_tablemeta(table, buf)
        buf.seek(0)
        table2 = load_tablemeta(buf)
        assert table2.table_name == table.table_name
        assert table2.total_files == table.total_files

    def test_empty_table(self) -> None:
        table = TableMeta(table_name="empty", format="iceberg")
        d = tablemeta_to_dict(table)
        table2 = tablemeta_from_dict(d)
        assert table2.table_name == "empty"
        assert table2.total_files == 0


class TestPlanIO:
    def _sample_plan(self) -> CompactionPlan:
        tasks = [
            CompactionTask(
                action=CompactionAction.MERGE,
                partition_key="dt=2024-01-01",
                target_files=["f1.parquet", "f2.parquet"],
                priority=5.0,
                reason="many small files",
            ),
            CompactionTask(
                action=CompactionAction.PRUNE,
                partition_key="dt=2023-01-01",
                target_files=["old.parquet"],
                priority=10.0,
                reason="stale partition",
            ),
        ]
        return CompactionPlan(
            table_name="events",
            tasks=tasks,
            estimated_size_reduction_bytes=1_000_000,
            estimated_file_reduction=10,
        )

    def test_roundtrip_jsonl(self) -> None:
        plan = self._sample_plan()
        buf = io.StringIO()
        plan_to_jsonl(plan, buf)
        buf.seek(0)
        plan2 = plan_from_jsonl(buf)
        assert plan.table_name == plan2.table_name
        assert len(plan.tasks) == len(plan2.tasks)
        assert plan2.tasks[0].action == CompactionAction.MERGE

    def test_first_line_is_meta(self) -> None:
        plan = self._sample_plan()
        buf = io.StringIO()
        plan_to_jsonl(plan, buf)
        buf.seek(0)
        meta = json.loads(buf.readline())
        assert "table_name" in meta
        assert "task_count" in meta

    def test_empty_raises(self) -> None:
        buf = io.StringIO()
        with pytest.raises(ValueError):
            plan_from_jsonl(buf)
