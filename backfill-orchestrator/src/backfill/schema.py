"""Core domain types for backfill orchestrator."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum


class PartitionState(str, Enum):
    """Lifecycle state of a single partition."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class Partition:
    """A single time-based partition unit.

    Args:
        partition_date: The date this partition covers.
        state:          Current lifecycle state.
        attempts:       Number of execution attempts so far.
        error_msg:      Last error message (if FAILED).
        started_at:     ISO timestamp when last run started.
        finished_at:    ISO timestamp when last run finished.
        priority:       Higher = scheduled earlier (default 0).
    """

    partition_date: datetime.date
    state: PartitionState = PartitionState.PENDING
    attempts: int = 0
    error_msg: str = ""
    started_at: str = ""
    finished_at: str = ""
    priority: int = 0

    def partition_key(self) -> str:
        return self.partition_date.isoformat()

    def to_dict(self) -> dict[str, object]:
        return {
            "partition_date": self.partition_date.isoformat(),
            "state": self.state.value,
            "attempts": self.attempts,
            "error_msg": self.error_msg,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Partition:
        def _s(k: str, default: str = "") -> str:
            v = d.get(k, default)
            return v if isinstance(v, str) else str(v)

        def _i(k: str, default: int = 0) -> int:
            v = d.get(k, default)
            return v if isinstance(v, int) else int(str(v))

        date_str = _s("partition_date")
        return cls(
            partition_date=datetime.date.fromisoformat(date_str),
            state=PartitionState(_s("state", "PENDING")),
            attempts=_i("attempts"),
            error_msg=_s("error_msg"),
            started_at=_s("started_at"),
            finished_at=_s("finished_at"),
            priority=_i("priority"),
        )


def date_range(
    start: datetime.date, end: datetime.date, step_days: int = 1
) -> list[datetime.date]:
    """Generate dates from start (inclusive) to end (inclusive)."""
    if step_days < 1:
        raise ValueError("step_days must be >= 1")
    dates: list[datetime.date] = []
    current = start
    while current <= end:
        dates.append(current)
        current += datetime.timedelta(days=step_days)
    return dates
