"""Backfill orchestrator: partition scheduling and state management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backfill.schema import Partition, PartitionState, date_range

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable


@dataclass
class BackfillJob:
    """Configuration for a backfill job."""

    job_id: str
    start_date: datetime.date
    end_date: datetime.date
    max_concurrency: int = 4
    max_retries: int = 3
    step_days: int = 1
    # Higher priority first
    reverse_chronological: bool = True  # newest partitions first (common pattern)

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.step_days < 1:
            raise ValueError("step_days must be >= 1")


class BackfillOrchestrator:
    """Stateful backfill orchestrator.

    Manages a queue of partitions, enforces max-concurrency,
    and tracks state across checkpoint/resume cycles.
    """

    def __init__(self, job: BackfillJob) -> None:
        self.job = job
        self._partitions: dict[str, Partition] = {}
        self._initialise()

    def _initialise(self) -> None:
        dates = date_range(self.job.start_date, self.job.end_date, self.job.step_days)
        for i, d in enumerate(dates):
            # Priority: reverse-chronological = higher priority for later dates
            prio = i if not self.job.reverse_chronological else len(dates) - i
            key = d.isoformat()
            if key not in self._partitions:
                self._partitions[key] = Partition(partition_date=d, priority=prio)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def partitions(self) -> list[Partition]:
        return list(self._partitions.values())

    def pending(self) -> list[Partition]:
        return [p for p in self._partitions.values() if p.state == PartitionState.PENDING]

    def running(self) -> list[Partition]:
        return [p for p in self._partitions.values() if p.state == PartitionState.RUNNING]

    def done(self) -> list[Partition]:
        return [p for p in self._partitions.values() if p.state == PartitionState.DONE]

    def failed(self) -> list[Partition]:
        return [p for p in self._partitions.values() if p.state == PartitionState.FAILED]

    def retryable(self) -> list[Partition]:
        """Failed partitions that have not exceeded max_retries."""
        return [
            p
            for p in self._partitions.values()
            if p.state == PartitionState.FAILED and p.attempts <= self.job.max_retries
        ]

    def progress(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in PartitionState}
        for p in self._partitions.values():
            counts[p.state.value] += 1
        return counts

    def is_complete(self) -> bool:
        return all(
            p.state in (PartitionState.DONE, PartitionState.SKIPPED)
            for p in self._partitions.values()
        )

    def next_runnable(self) -> list[Partition]:
        """Return up to max_concurrency - current_running partitions to schedule."""
        available_slots = self.job.max_concurrency - len(self.running())
        if available_slots <= 0:
            return []
        candidates = sorted(
            self.pending() + self.retryable(),
            key=lambda p: (-p.priority, p.partition_date),
        )
        return candidates[:available_slots]

    def mark_running(self, partition_date: datetime.date, started_at: str = "") -> None:
        key = partition_date.isoformat()
        p = self._partitions[key]
        p.state = PartitionState.RUNNING
        p.attempts += 1
        p.started_at = started_at
        p.error_msg = ""

    def mark_done(self, partition_date: datetime.date, finished_at: str = "") -> None:
        key = partition_date.isoformat()
        p = self._partitions[key]
        p.state = PartitionState.DONE
        p.finished_at = finished_at

    def mark_failed(
        self, partition_date: datetime.date, error_msg: str = "", finished_at: str = ""
    ) -> None:
        key = partition_date.isoformat()
        p = self._partitions[key]
        p.state = PartitionState.FAILED
        p.error_msg = error_msg
        p.finished_at = finished_at

    def mark_skipped(self, partition_date: datetime.date) -> None:
        key = partition_date.isoformat()
        self._partitions[key].state = PartitionState.SKIPPED

    def reset_failed(self) -> int:
        """Reset all FAILED partitions to PENDING for retry. Returns count."""
        count = 0
        for p in self._partitions.values():
            if p.state == PartitionState.FAILED:
                p.state = PartitionState.PENDING
                count += 1
        return count

    def run_sync(
        self,
        execute_fn: Callable[[datetime.date], None],
        now_fn: Callable[[], str] | None = None,
    ) -> dict[str, int]:
        """Run all partitions synchronously (for testing/simple use cases).

        Args:
            execute_fn: Function called with each partition_date. Should raise
                        on failure. Must not be called concurrently.
            now_fn:     Returns current ISO timestamp string. Defaults to empty str.

        Returns:
            Progress counts after completion.
        """
        _now = now_fn or (lambda: "")

        while True:
            runnable = self.next_runnable()
            if not runnable and not self.running():
                break
            for p in runnable:
                self.mark_running(p.partition_date, started_at=_now())
                try:
                    execute_fn(p.partition_date)
                    self.mark_done(p.partition_date, finished_at=_now())
                except Exception as exc:
                    self.mark_failed(
                        p.partition_date,
                        error_msg=str(exc),
                        finished_at=_now(),
                    )

        return self.progress()

    # ------------------------------------------------------------------
    # Checkpoint / restore
    # ------------------------------------------------------------------

    def to_jsonl(self) -> str:
        lines = [json.dumps(p.to_dict(), ensure_ascii=False) for p in self._partitions.values()]
        return "\n".join(lines) + ("\n" if lines else "")

    @classmethod
    def from_jsonl(cls, job: BackfillJob, text: str) -> BackfillOrchestrator:
        """Restore orchestrator state from a JSONL checkpoint."""
        orch = cls(job)
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not isinstance(d, dict):
                continue
            p = Partition.from_dict(d)
            orch._partitions[p.partition_key()] = p
        return orch
