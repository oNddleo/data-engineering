"""Tests for JSONL serialisation."""

from __future__ import annotations

import io
import json

from dpbudget.io_jsonl import (
    analyst_from_dict,
    analyst_to_dict,
    budget_from_dict,
    budget_to_dict,
    dataset_from_dict,
    dataset_to_dict,
    log_from_dict,
    log_to_dict,
    read_log,
    write_log,
)
from dpbudget.schema import (
    Analyst,
    BudgetAllocation,
    Dataset,
    Mechanism,
    QueryLogEntry,
    QueryStatus,
)


def _entry() -> QueryLogEntry:
    return QueryLogEntry(
        query_id="q1",
        dataset_id="ds",
        analyst_id="alice",
        query_text="SELECT COUNT(*)",
        true_result=100.0,
        noisy_result=103.5,
        noise_added=3.5,
        epsilon_requested=0.5,
        delta_requested=0.0,
        epsilon_consumed=0.5,
        delta_consumed=0.0,
        sensitivity=1.0,
        mechanism_used=Mechanism.LAPLACE,
        status=QueryStatus.ALLOWED,
        budget_remaining_after=1.5,
    )


class TestDatasetSerde:
    def test_roundtrip(self) -> None:
        d = Dataset("patients", "Patient Records", sensitivity=50.0)
        assert dataset_from_dict(dataset_to_dict(d)) == d

    def test_json_serialisable(self) -> None:
        d = Dataset("banking", "Bank Txns")
        json.dumps(dataset_to_dict(d))  # no exception


class TestAnalystSerde:
    def test_roundtrip(self) -> None:
        a = Analyst("alice", "Alice Chen", "alice@example.com")
        assert analyst_from_dict(analyst_to_dict(a)) == a


class TestBudgetSerde:
    def test_roundtrip(self) -> None:
        b = BudgetAllocation(
            dataset_id="ds",
            analyst_id="alice",
            epsilon_total=3.0,
            consumed_epsilon=1.0,
        )
        b2 = budget_from_dict(budget_to_dict(b))
        assert b2.dataset_id == b.dataset_id
        assert abs(b2.epsilon_total - 3.0) < 1e-9
        assert abs(b2.consumed_epsilon - 1.0) < 1e-9


class TestLogSerde:
    def test_roundtrip_dict(self) -> None:
        e = _entry()
        e2 = log_from_dict(log_to_dict(e))
        assert e2.query_id == e.query_id
        assert abs(e2.noisy_result - e.noisy_result) < 1e-9  # type: ignore[operator]

    def test_roundtrip_jsonl(self) -> None:
        entries = [_entry()]
        buf = io.StringIO()
        write_log(entries, buf)
        buf.seek(0)
        result = read_log(buf)
        assert len(result) == 1
        assert result[0].query_id == "q1"

    def test_blocked_entry_null_result(self) -> None:
        e = QueryLogEntry(
            query_id="q2",
            dataset_id="ds",
            analyst_id="bob",
            query_text="",
            true_result=0.0,
            noisy_result=None,
            noise_added=None,
            epsilon_requested=1.0,
            delta_requested=0.0,
            epsilon_consumed=0.0,
            delta_consumed=0.0,
            sensitivity=1.0,
            mechanism_used=Mechanism.LAPLACE,
            status=QueryStatus.BLOCKED,
            budget_remaining_after=0.0,
        )
        e2 = log_from_dict(log_to_dict(e))
        assert e2.noisy_result is None
        assert e2.status == QueryStatus.BLOCKED

    def test_empty_file(self) -> None:
        buf = io.StringIO("")
        assert read_log(buf) == []
