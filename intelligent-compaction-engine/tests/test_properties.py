"""Hypothesis property tests for compaction engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from compact.engine import _score_columns, plan
from compact.schema import DataFile, Partition, QueryPattern, TableMeta

_NOW = datetime.now(tz=timezone.utc)


def _file(size_bytes: int, days_old: int = 5, part: str = "p") -> DataFile:
    ts = _NOW - timedelta(days=days_old)
    return DataFile(
        path=f"s3://b/t/{part}/f-{size_bytes}.parquet",
        size_bytes=size_bytes,
        row_count=size_bytes // 200,
        partition=part,
        created_at=ts,
        last_modified=ts,
    )


class TestScoreColumnsProperties:
    @given(
        st.lists(
            st.text(min_size=1, max_size=20),
            min_size=1,
            max_size=10,
        )
    )
    def test_scores_sum_to_1(self, cols: list[str]) -> None:
        qp = QueryPattern("q1", filter_columns=cols, frequency=1)
        scores = _score_columns([qp])
        total = sum(scores.values())
        assert abs(total - 1.0) < 1e-9

    @given(
        st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=5,
        )
    )
    def test_scores_non_negative(self, freqs: list[int]) -> None:
        patterns = [
            QueryPattern(f"q{i}", filter_columns=[f"col{i}"], frequency=f)
            for i, f in enumerate(freqs)
        ]
        scores = _score_columns(patterns)
        assert all(v >= 0 for v in scores.values())


class TestPlanProperties:
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_plan_has_no_tasks_for_empty_partitions(self, n: int) -> None:
        partitions = [Partition(key=f"p{i}") for i in range(n)]
        table = TableMeta(table_name="t", format="delta", partitions=partitions)
        result = plan(table)
        assert result.tasks == []

    @given(st.integers(min_value=0, max_value=99))
    @settings(max_examples=30)
    def test_tasks_sorted_descending_priority(self, seed: int) -> None:
        from compact.simulator import generate_query_patterns, generate_table

        table = generate_table(n_partitions=10, seed=seed)
        patterns = generate_query_patterns(n_patterns=20, seed=seed)
        result = plan(table, query_patterns=patterns)
        prios = [t.priority for t in result.tasks]
        assert prios == sorted(prios, reverse=True)

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20)
    def test_action_counts_match_task_count(self, n: int) -> None:
        from compact.simulator import generate_table

        table = generate_table(n_partitions=n, seed=n)
        result = plan(table)
        assert sum(result.action_counts.values()) == len(result.tasks)

    @given(
        st.integers(min_value=1, max_value=10),
        st.integers(min_value=3, max_value=15),
    )
    @settings(max_examples=30)
    def test_small_files_trigger_merge(self, n_parts: int, n_files: int) -> None:
        # All files are tiny (1 MiB each), should trigger merge
        small = 1 * 1024 * 1024
        partitions = [
            Partition(
                key=f"p{i}",
                files=[_file(small, days_old=1, part=f"p{i}") for _ in range(n_files)],
            )
            for i in range(n_parts)
        ]
        table = TableMeta(table_name="t", format="delta", partitions=partitions)
        result = plan(table, prune_after_days=365)
        merge_tasks = [t for t in result.tasks if t.action.value == "merge"]
        assert len(merge_tasks) == n_parts
