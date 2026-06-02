"""Tests for backfill orchestrator."""

from __future__ import annotations

import datetime

import pytest

from backfill.orchestrator import BackfillJob, BackfillOrchestrator
from backfill.schema import PartitionState


def _job(
    start: str = "2025-01-01",
    end: str = "2025-01-07",
    max_concurrency: int = 2,
    max_retries: int = 1,
) -> BackfillJob:
    return BackfillJob(
        job_id="test-job",
        start_date=datetime.date.fromisoformat(start),
        end_date=datetime.date.fromisoformat(end),
        max_concurrency=max_concurrency,
        max_retries=max_retries,
    )


class TestInitialisation:
    def test_creates_correct_partition_count(self) -> None:
        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-07"))
        assert len(orch.partitions) == 7

    def test_all_start_pending(self) -> None:
        orch = BackfillOrchestrator(_job())
        assert all(p.state == PartitionState.PENDING for p in orch.partitions)

    def test_step_days(self) -> None:
        job = BackfillJob(
            job_id="j",
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 1, 31),
            step_days=7,
        )
        orch = BackfillOrchestrator(job)
        # Jan 1, 8, 15, 22, 29 = 5 partitions
        assert len(orch.partitions) == 5

    def test_invalid_date_range_raises(self) -> None:
        with pytest.raises(ValueError):
            BackfillJob(
                job_id="j",
                start_date=datetime.date(2025, 2, 1),
                end_date=datetime.date(2025, 1, 1),
            )

    def test_invalid_concurrency_raises(self) -> None:
        with pytest.raises(ValueError):
            BackfillJob(
                job_id="j",
                start_date=datetime.date(2025, 1, 1),
                end_date=datetime.date(2025, 1, 7),
                max_concurrency=0,
            )


class TestStateTransitions:
    def test_mark_running_increments_attempts(self) -> None:
        orch = BackfillOrchestrator(_job())
        d = datetime.date(2025, 1, 1)
        orch.mark_running(d)
        p = orch._partitions[d.isoformat()]
        assert p.state == PartitionState.RUNNING
        assert p.attempts == 1

    def test_mark_done(self) -> None:
        orch = BackfillOrchestrator(_job())
        d = datetime.date(2025, 1, 1)
        orch.mark_running(d)
        orch.mark_done(d, finished_at="2025-01-01T12:00:00")
        p = orch._partitions[d.isoformat()]
        assert p.state == PartitionState.DONE
        assert p.finished_at == "2025-01-01T12:00:00"

    def test_mark_failed(self) -> None:
        orch = BackfillOrchestrator(_job())
        d = datetime.date(2025, 1, 2)
        orch.mark_running(d)
        orch.mark_failed(d, error_msg="timeout")
        p = orch._partitions[d.isoformat()]
        assert p.state == PartitionState.FAILED
        assert p.error_msg == "timeout"

    def test_mark_skipped(self) -> None:
        orch = BackfillOrchestrator(_job())
        d = datetime.date(2025, 1, 3)
        orch.mark_skipped(d)
        assert orch._partitions[d.isoformat()].state == PartitionState.SKIPPED

    def test_reset_failed(self) -> None:
        orch = BackfillOrchestrator(_job())
        d = datetime.date(2025, 1, 1)
        orch.mark_running(d)
        orch.mark_failed(d)
        count = orch.reset_failed()
        assert count == 1
        assert orch._partitions[d.isoformat()].state == PartitionState.PENDING


class TestScheduling:
    def test_next_runnable_respects_concurrency(self) -> None:
        orch = BackfillOrchestrator(_job(max_concurrency=2))
        runnable = orch.next_runnable()
        assert len(runnable) == 2

    def test_next_runnable_empty_when_full(self) -> None:
        orch = BackfillOrchestrator(_job(max_concurrency=1))
        d = datetime.date(2025, 1, 1)
        orch.mark_running(d)
        assert orch.next_runnable() == []

    def test_next_runnable_includes_retryable(self) -> None:
        orch = BackfillOrchestrator(_job(max_concurrency=3, max_retries=2))
        d = datetime.date(2025, 1, 1)
        orch.mark_running(d)
        orch.mark_failed(d)
        runnable = orch.next_runnable()
        dates = [r.partition_date for r in runnable]
        assert d in dates

    def test_failed_beyond_max_retries_not_runnable(self) -> None:
        orch = BackfillOrchestrator(_job(max_concurrency=5, max_retries=1))
        d = datetime.date(2025, 1, 1)
        # Exceed retries: attempts > max_retries
        orch.mark_running(d)
        orch.mark_failed(d)
        orch.mark_running(d)
        orch.mark_failed(d)  # attempts=2 > max_retries=1
        runnable = orch.next_runnable()
        dates = [r.partition_date for r in runnable]
        assert d not in dates


class TestRunSync:
    def test_all_succeed(self) -> None:
        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-03"))
        progress = orch.run_sync(lambda _: None)
        assert progress["DONE"] == 3
        assert progress["FAILED"] == 0
        assert orch.is_complete()

    def test_all_fail(self) -> None:
        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-03", max_retries=0))

        def _fail(_: datetime.date) -> None:
            raise RuntimeError("boom")

        orch.run_sync(_fail)
        assert orch.progress()["FAILED"] == 3

    def test_partial_failure_retry(self) -> None:
        fail_dates = {datetime.date(2025, 1, 2)}
        attempt_counts: dict[str, int] = {}

        def _execute(d: datetime.date) -> None:
            key = d.isoformat()
            attempt_counts[key] = attempt_counts.get(key, 0) + 1
            if d in fail_dates and attempt_counts[key] == 1:
                raise RuntimeError("first attempt fails")

        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-03", max_retries=1))
        orch.run_sync(_execute)
        assert orch.progress()["DONE"] >= 2


class TestCheckpoint:
    def test_roundtrip(self) -> None:
        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-05"))
        orch.mark_running(datetime.date(2025, 1, 1))
        orch.mark_done(datetime.date(2025, 1, 1))
        text = orch.to_jsonl()
        restored = BackfillOrchestrator.from_jsonl(_job("2025-01-01", "2025-01-05"), text)
        assert restored._partitions["2025-01-01"].state == PartitionState.DONE
        assert restored._partitions["2025-01-02"].state == PartitionState.PENDING

    def test_is_complete_after_all_done(self) -> None:
        orch = BackfillOrchestrator(_job("2025-01-01", "2025-01-02"))
        for d in [datetime.date(2025, 1, 1), datetime.date(2025, 1, 2)]:
            orch.mark_running(d)
            orch.mark_done(d)
        assert orch.is_complete()
