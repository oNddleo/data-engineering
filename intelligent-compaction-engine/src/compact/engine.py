"""Compaction planner: query-pattern analysis + file scoring + action generation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from compact.schema import (
    CompactionAction,
    CompactionPlan,
    CompactionTask,
    Partition,
    QueryPattern,
    TableMeta,
)

_DEFAULT_TARGET_FILE_SIZE = 128 * 1024 * 1024  # 128 MiB
_SMALL_FILE_RATIO = 0.25  # file is "small" if < 25% of target size
_PRUNE_AFTER_DAYS = 90
_MIN_FILES_FOR_MERGE = 3


def _score_columns(patterns: list[QueryPattern]) -> dict[str, float]:
    """Return a frequency-weighted importance score per column."""
    scores: Counter[str] = Counter()
    for qp in patterns:
        w = qp.frequency
        for col in qp.filter_columns:
            scores[col] += 3 * w
        for col in qp.join_columns:
            scores[col] += 2 * w
        for col in qp.group_by_columns:
            scores[col] += 1 * w
    total = sum(scores.values()) or 1
    return {col: cnt / total for col, cnt in scores.items()}


def _partition_needs_merge(
    partition: Partition,
    target_size: int,
) -> bool:
    small = [f for f in partition.files if f.size_bytes < target_size * _SMALL_FILE_RATIO]
    return len(small) >= _MIN_FILES_FOR_MERGE


def _partition_is_stale(partition: Partition, prune_after_days: int) -> bool:
    if not partition.files:
        return False
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=prune_after_days)
    return all(f.last_modified < cutoff for f in partition.files)


def _build_merge_task(partition: Partition, priority: float) -> CompactionTask:
    small_files = [
        f.path
        for f in partition.files
        if f.size_bytes < _DEFAULT_TARGET_FILE_SIZE * _SMALL_FILE_RATIO
    ]
    current_count = len(small_files)
    ideal_count = max(1, partition.total_size_bytes // _DEFAULT_TARGET_FILE_SIZE)
    return CompactionTask(
        action=CompactionAction.MERGE,
        partition_key=partition.key,
        target_files=small_files,
        priority=priority,
        reason=f"{current_count} small files → ~{ideal_count} merged file(s)",
    )


def _build_zorder_task(
    partition: Partition,
    z_cols: list[str],
    priority: float,
) -> CompactionTask:
    return CompactionTask(
        action=CompactionAction.ZORDER,
        partition_key=partition.key,
        target_files=[f.path for f in partition.files],
        z_order_columns=z_cols,
        priority=priority,
        reason=f"Z-order by {z_cols} to improve query pruning",
    )


def _build_prune_task(partition: Partition, priority: float) -> CompactionTask:
    return CompactionTask(
        action=CompactionAction.PRUNE,
        partition_key=partition.key,
        target_files=[f.path for f in partition.files],
        priority=priority,
        reason=f"Partition not modified in >{_PRUNE_AFTER_DAYS}d",
    )


class CompactionEngine:
    """Plan compaction actions for a lakehouse table based on query patterns."""

    def __init__(
        self,
        target_file_size: int = _DEFAULT_TARGET_FILE_SIZE,
        prune_after_days: int = _PRUNE_AFTER_DAYS,
        top_zorder_columns: int = 4,
    ) -> None:
        self.target_file_size = target_file_size
        self.prune_after_days = prune_after_days
        self.top_zorder_columns = top_zorder_columns

    def plan(
        self,
        table: TableMeta,
        query_patterns: list[QueryPattern] | None = None,
    ) -> CompactionPlan:
        """Generate a compaction plan for the given table."""
        patterns = query_patterns or []
        col_scores = _score_columns(patterns)
        z_cols = sorted(col_scores, key=lambda c: col_scores[c], reverse=True)[
            : self.top_zorder_columns
        ]
        # Filter to columns that actually exist in the table
        if table.columns:
            z_cols = [c for c in z_cols if c in table.columns]

        tasks: list[CompactionTask] = []
        pruned_bytes = 0
        pruned_files = 0

        for partition in table.partitions:
            if not partition.files:
                continue

            # Prune stale partitions first (highest priority)
            if _partition_is_stale(partition, self.prune_after_days):
                tasks.append(_build_prune_task(partition, priority=10.0))
                pruned_bytes += partition.total_size_bytes
                pruned_files += partition.file_count
                continue

            # Merge small files
            if _partition_needs_merge(partition, self.target_file_size):
                merge_priority = partition.file_count / max(1, partition.total_size_bytes / 1e9)
                tasks.append(_build_merge_task(partition, priority=merge_priority))
                pruned_files += max(0, partition.file_count - 1)

            # Z-order if we have hot columns and multiple files
            if z_cols and partition.file_count >= 2:
                z_priority = sum(col_scores.get(c, 0) for c in z_cols)
                tasks.append(_build_zorder_task(partition, z_cols, priority=z_priority))

        tasks.sort(key=lambda t: t.priority, reverse=True)

        return CompactionPlan(
            table_name=table.table_name,
            tasks=tasks,
            estimated_size_reduction_bytes=pruned_bytes,
            estimated_file_reduction=pruned_files,
        )


def plan(
    table: TableMeta,
    query_patterns: list[QueryPattern] | None = None,
    target_file_size: int = _DEFAULT_TARGET_FILE_SIZE,
    prune_after_days: int = _PRUNE_AFTER_DAYS,
) -> CompactionPlan:
    """Functional entry-point for compaction planning."""
    return CompactionEngine(
        target_file_size=target_file_size,
        prune_after_days=prune_after_days,
    ).plan(table, query_patterns)
