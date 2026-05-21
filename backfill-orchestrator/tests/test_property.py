"""Property-based tests for backfill orchestrator."""

from __future__ import annotations

import datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from backfill.orchestrator import BackfillJob, BackfillOrchestrator
from backfill.schema import PartitionState


def _date(d_int: int) -> datetime.date:
    return datetime.date(2025, 1, 1) + datetime.timedelta(days=d_int)


@given(
    n_days=st.integers(min_value=1, max_value=30),
    concurrency=st.integers(min_value=1, max_value=8),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_dry_run_all_done(n_days: int, concurrency: int) -> None:
    """Running with a no-op executor should mark all partitions DONE."""
    start = datetime.date(2025, 1, 1)
    end = start + datetime.timedelta(days=n_days - 1)
    job = BackfillJob(
        job_id="prop-test",
        start_date=start,
        end_date=end,
        max_concurrency=concurrency,
    )
    orch = BackfillOrchestrator(job)
    orch.run_sync(lambda _: None)
    assert all(p.state == PartitionState.DONE for p in orch.partitions)


@given(
    n_days=st.integers(min_value=1, max_value=14),
    max_retries=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_always_fail_leaves_all_failed(n_days: int, max_retries: int) -> None:
    start = datetime.date(2025, 1, 1)
    end = start + datetime.timedelta(days=n_days - 1)
    job = BackfillJob(
        job_id="fail-test",
        start_date=start,
        end_date=end,
        max_retries=max_retries,
    )
    orch = BackfillOrchestrator(job)

    def _fail(_: datetime.date) -> None:
        raise RuntimeError("always fail")

    orch.run_sync(_fail)
    assert all(p.state == PartitionState.FAILED for p in orch.partitions)
    # Each partition should have been attempted max_retries + 1 times
    for p in orch.partitions:
        assert p.attempts == max_retries + 1


@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=20)
def test_partition_count_equals_days(n_days: int) -> None:
    start = datetime.date(2025, 1, 1)
    end = start + datetime.timedelta(days=n_days - 1)
    job = BackfillJob(job_id="count-test", start_date=start, end_date=end)
    orch = BackfillOrchestrator(job)
    assert len(orch.partitions) == n_days


@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=20)
def test_progress_sums_to_partition_count(n_days: int) -> None:
    start = datetime.date(2025, 1, 1)
    end = start + datetime.timedelta(days=n_days - 1)
    job = BackfillJob(job_id="sum-test", start_date=start, end_date=end)
    orch = BackfillOrchestrator(job)
    progress = orch.progress()
    assert sum(progress.values()) == n_days
