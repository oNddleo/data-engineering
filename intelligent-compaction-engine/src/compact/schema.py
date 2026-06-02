"""Domain types for the compaction engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime  # noqa: TCH003


class CompactionAction(str, enum.Enum):
    MERGE = "merge"
    ZORDER = "zorder"
    PRUNE = "prune"
    VACUUM = "vacuum"
    SKIP = "skip"


@dataclass
class DataFile:
    path: str
    size_bytes: int
    row_count: int
    partition: str
    created_at: datetime
    last_modified: datetime


@dataclass
class Partition:
    key: str
    files: list[DataFile] = field(default_factory=list)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def avg_file_size_bytes(self) -> float:
        if not self.files:
            return 0.0
        return self.total_size_bytes / len(self.files)


@dataclass
class TableMeta:
    table_name: str
    format: str
    partitions: list[Partition] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return sum(p.file_count for p in self.partitions)

    @property
    def total_size_bytes(self) -> int:
        return sum(p.total_size_bytes for p in self.partitions)


@dataclass
class QueryPattern:
    query_id: str
    filter_columns: list[str] = field(default_factory=list)
    join_columns: list[str] = field(default_factory=list)
    group_by_columns: list[str] = field(default_factory=list)
    frequency: int = 1


@dataclass
class CompactionTask:
    action: CompactionAction
    partition_key: str
    target_files: list[str]
    z_order_columns: list[str] = field(default_factory=list)
    priority: float = 0.0
    reason: str = ""


@dataclass
class CompactionPlan:
    table_name: str
    tasks: list[CompactionTask] = field(default_factory=list)
    estimated_size_reduction_bytes: int = 0
    estimated_file_reduction: int = 0

    @property
    def action_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in self.tasks:
            counts[t.action.value] = counts.get(t.action.value, 0) + 1
        return counts
