"""Tests for the exactlyonce package — 40+ tests including Hypothesis."""

from __future__ import annotations

import json
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from exactlyonce.coordinator import SagaState, TransactionCoordinator
from exactlyonce.dlq import DeadLetterQueue
from exactlyonce.idempotency import IdempotencyLog
from exactlyonce.outbox import OutboxEntry, OutboxStore
from exactlyonce.pipeline import ExactlyOncePipeline
from exactlyonce.recovery import RecoveryAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp_path() -> Path:
    """Return a fresh temp directory Path (caller's test owns lifecycle)."""
    d = tempfile.mkdtemp()
    return Path(d)


def _make_event(event_id: str = "evt-001", amount: int = 100) -> dict[str, object]:
    return {"event_id": event_id, "amount": amount}


# ===========================================================================
# TestIdempotencyLog
# ===========================================================================


class TestIdempotencyLog:
    def test_has_seen_initially_false(self) -> None:
        log = IdempotencyLog()
        assert log.has_seen("x") is False

    def test_mark_and_has_seen(self) -> None:
        log = IdempotencyLog()
        log.mark_seen("evt-1", "consumer-a")
        assert log.has_seen("evt-1") is True

    def test_different_event_not_seen(self) -> None:
        log = IdempotencyLog()
        log.mark_seen("evt-1", "consumer-a")
        assert log.has_seen("evt-2") is False

    def test_mark_seen_idempotent(self) -> None:
        log = IdempotencyLog()
        log.mark_seen("evt-1", "consumer-a")
        log.mark_seen("evt-1", "consumer-b")  # second call is a no-op
        assert log.count() == 1

    def test_per_consumer_isolation(self) -> None:
        """Two different consumers should see independent state."""
        log_a = IdempotencyLog()
        log_b = IdempotencyLog()
        log_a.mark_seen("evt-1", "consumer-a")
        assert log_b.has_seen("evt-1") is False

    def test_custom_timestamp(self) -> None:
        log = IdempotencyLog()
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        log.mark_seen("evt-ts", "consumer-a", ts=ts)
        entries = log.all_entries()
        assert len(entries) == 1
        assert "2024-01-01" in entries[0]["ts"]

    def test_count_increments(self) -> None:
        log = IdempotencyLog()
        for i in range(5):
            log.mark_seen(f"evt-{i}", "c")
        assert log.count() == 5

    def test_jsonl_persistence_round_trip(self) -> None:
        p = _tmp_path() / "idem.jsonl"
        log = IdempotencyLog(persistence_path=p)
        log.mark_seen("persist-1", "consumer-x")
        log.mark_seen("persist-2", "consumer-y")

        # Load from disk into new instance
        log2 = IdempotencyLog(persistence_path=p)
        assert log2.has_seen("persist-1")
        assert log2.has_seen("persist-2")
        assert log2.count() == 2

    def test_jsonl_persistence_does_not_duplicate(self) -> None:
        p = _tmp_path() / "idem2.jsonl"
        log = IdempotencyLog(persistence_path=p)
        log.mark_seen("e-dup", "c")
        log2 = IdempotencyLog(persistence_path=p)
        # Adding same event in reloaded log should not increase count
        log2.mark_seen("e-dup", "c")
        assert log2.count() == 1

    def test_thread_safety(self) -> None:
        log = IdempotencyLog()
        errors: list[str] = []

        def worker(event_id: str) -> None:
            try:
                log.mark_seen(event_id, "consumer")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(f"tid-{i}",)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert log.count() == 50


# ===========================================================================
# TestOutboxStore
# ===========================================================================


class TestOutboxStore:
    def test_put_and_get(self) -> None:
        store = OutboxStore()
        entry = OutboxEntry(event_id="e1", payload={"x": 1})
        store.put(entry)
        fetched = store.get("e1")
        assert fetched is not None
        assert fetched.event_id == "e1"

    def test_get_missing_returns_none(self) -> None:
        store = OutboxStore()
        assert store.get("nonexistent") is None

    def test_pending_returns_pending_entries(self) -> None:
        store = OutboxStore()
        store.put(OutboxEntry(event_id="p1", payload={}))
        store.put(OutboxEntry(event_id="p2", payload={}))
        pending = store.pending()
        ids = {e.event_id for e in pending}
        assert "p1" in ids
        assert "p2" in ids

    def test_mark_published_removes_from_pending(self) -> None:
        store = OutboxStore()
        store.put(OutboxEntry(event_id="pub1", payload={}))
        store.mark_published("pub1")
        assert store.pending() == []
        entry = store.get("pub1")
        assert entry is not None
        assert entry.status == "PUBLISHED"
        assert entry.published_at is not None

    def test_mark_failed_increments_retry_count(self) -> None:
        store = OutboxStore()
        store.put(OutboxEntry(event_id="fail1", payload={}))
        store.mark_failed("fail1")
        entry = store.get("fail1")
        assert entry is not None
        assert entry.status == "FAILED"
        assert entry.retry_count == 1

    def test_mark_failed_multiple_times(self) -> None:
        store = OutboxStore()
        store.put(OutboxEntry(event_id="fail2", payload={}))
        store.mark_failed("fail2")
        store.put(OutboxEntry(event_id="fail2", payload={}, status="PENDING"))
        store.mark_failed("fail2")
        entry = store.get("fail2")
        assert entry is not None
        assert entry.retry_count == 1

    def test_mark_published_unknown_raises(self) -> None:
        store = OutboxStore()
        with pytest.raises(KeyError):
            store.mark_published("unknown")

    def test_mark_failed_unknown_raises(self) -> None:
        store = OutboxStore()
        with pytest.raises(KeyError):
            store.mark_failed("unknown")

    def test_persistence_round_trip(self) -> None:
        p = _tmp_path() / "outbox.jsonl"
        store = OutboxStore(persistence_path=p)
        store.put(OutboxEntry(event_id="o1", payload={"k": "v"}))
        store.mark_published("o1")

        store2 = OutboxStore(persistence_path=p)
        entry = store2.get("o1")
        assert entry is not None
        assert entry.status == "PUBLISHED"
        assert entry.payload == {"k": "v"}

    def test_thread_safety(self) -> None:
        store = OutboxStore()
        errors: list[str] = []

        def worker(i: int) -> None:
            try:
                store.put(OutboxEntry(event_id=f"te-{i}", payload={"i": i}))
                store.mark_published(f"te-{i}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ===========================================================================
# TestTransactionCoordinator
# ===========================================================================


class TestTransactionCoordinator:
    def _full_advance(self, coord: TransactionCoordinator, saga_id: str) -> None:
        for step in ("kafka_publish", "warehouse_ack", "notification_ack", "complete"):
            coord.advance(saga_id, step)

    def test_begin_returns_saga_id(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e1", {"x": 1})
        assert isinstance(saga_id, str)
        assert len(saga_id) > 0

    def test_initial_state_is_pending(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e1", {})
        saga = coord.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.PENDING

    def test_full_happy_path_reaches_completed(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e2", {})
        self._full_advance(coord, saga_id)
        saga = coord.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.COMPLETED

    def test_invalid_transition_raises(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e3", {})
        with pytest.raises(ValueError):
            coord.advance(saga_id, "invalid_step")

    def test_compensate_sets_compensating(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e4", {})
        coord.compensate(saga_id)
        saga = coord.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.COMPENSATING

    def test_compensate_from_compensating_to_compensated(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e5", {})
        coord.compensate(saga_id)
        coord.advance(saga_id, "compensated")
        saga = coord.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.COMPENSATED

    def test_get_unknown_returns_none(self) -> None:
        coord = TransactionCoordinator()
        assert coord.get("nonexistent") is None

    def test_steps_recorded(self) -> None:
        coord = TransactionCoordinator()
        saga_id = coord.begin("e6", {})
        coord.advance(saga_id, "kafka_publish")
        saga = coord.get(saga_id)
        assert saga is not None
        assert "kafka_publish" in saga.steps

    def test_persistence_round_trip(self) -> None:
        p = _tmp_path() / "coord.jsonl"
        coord = TransactionCoordinator(persistence_path=p)
        saga_id = coord.begin("e7", {"amount": 42})
        coord.advance(saga_id, "kafka_publish")

        coord2 = TransactionCoordinator(persistence_path=p)
        saga = coord2.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.KAFKA_PUBLISHED

    def test_concurrent_sagas(self) -> None:
        coord = TransactionCoordinator()
        saga_ids: list[str] = []
        lock = threading.Lock()
        errors: list[str] = []

        def worker(i: int) -> None:
            try:
                sid = coord.begin(f"ce-{i}", {"i": i})
                with lock:
                    saga_ids.append(sid)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(saga_ids) == 30


# ===========================================================================
# TestExactlyOncePipeline
# ===========================================================================


class TestExactlyOncePipeline:
    def test_happy_path_returns_completed(self) -> None:
        pipeline = ExactlyOncePipeline()
        result = pipeline.process(_make_event("hp-1"))
        assert result.status == SagaState.COMPLETED
        assert result.skipped_duplicate is False
        assert result.saga_id is not None

    def test_duplicate_is_skipped(self) -> None:
        pipeline = ExactlyOncePipeline()
        pipeline.process(_make_event("dup-1"))
        result2 = pipeline.process(_make_event("dup-1"))
        assert result2.skipped_duplicate is True
        assert result2.saga_id is None

    def test_saga_reaches_completed_state(self) -> None:
        coord = TransactionCoordinator()
        pipeline = ExactlyOncePipeline(coordinator=coord)
        result = pipeline.process(_make_event("saga-1"))
        saga = coord.get(result.saga_id or "")
        assert saga is not None
        assert saga.state == SagaState.COMPLETED

    def test_outbox_entry_published(self) -> None:
        outbox = OutboxStore()
        pipeline = ExactlyOncePipeline(outbox=outbox)
        pipeline.process(_make_event("ob-1"))
        entry = outbox.get("ob-1")
        assert entry is not None
        assert entry.status == "PUBLISHED"

    def test_event_marked_in_idempotency_log(self) -> None:
        idem = IdempotencyLog()
        pipeline = ExactlyOncePipeline(idempotency_log=idem)
        pipeline.process(_make_event("idem-1"))
        assert idem.has_seen("idem-1")

    def test_event_without_event_id_gets_one(self) -> None:
        pipeline = ExactlyOncePipeline()
        event: dict[str, object] = {"amount": 50}
        result = pipeline.process(event)
        assert result.status == SagaState.COMPLETED
        assert "event_id" in event  # mutated in-place

    def test_different_events_processed_independently(self) -> None:
        pipeline = ExactlyOncePipeline()
        r1 = pipeline.process(_make_event("ind-1"))
        r2 = pipeline.process(_make_event("ind-2"))
        assert r1.saga_id != r2.saga_id
        assert r1.skipped_duplicate is False
        assert r2.skipped_duplicate is False

    def test_consumer_name_recorded(self) -> None:
        idem = IdempotencyLog()
        pipeline = ExactlyOncePipeline(idempotency_log=idem, consumer_name="my-consumer")
        pipeline.process(_make_event("cn-1"))
        entries = idem.all_entries()
        assert len(entries) == 1
        assert entries[0]["consumer"] == "my-consumer"


# ===========================================================================
# TestDeadLetterQueue
# ===========================================================================


class TestDeadLetterQueue:
    def test_enqueue_increments_count(self) -> None:
        dlq = DeadLetterQueue()
        dlq.enqueue({"id": "1"}, "test reason")
        assert dlq.count() == 1

    def test_drain_removes_entries(self) -> None:
        dlq = DeadLetterQueue()
        dlq.enqueue({"id": "1"}, "r1")
        dlq.enqueue({"id": "2"}, "r2")
        drained = dlq.drain(max=10)
        assert len(drained) == 2
        assert dlq.count() == 0

    def test_drain_respects_max(self) -> None:
        dlq = DeadLetterQueue()
        for i in range(10):
            dlq.enqueue({"id": str(i)}, "r")
        drained = dlq.drain(max=3)
        assert len(drained) == 3
        assert dlq.count() == 7

    def test_drain_empty_returns_empty_list(self) -> None:
        dlq = DeadLetterQueue()
        assert dlq.drain() == []

    def test_entry_fields(self) -> None:
        dlq = DeadLetterQueue()
        entry = dlq.enqueue({"id": "x"}, "bad event", source_consumer="c-1")
        assert entry.reason == "bad event"
        assert entry.source_consumer == "c-1"
        assert entry.event == {"id": "x"}
        assert entry.dlq_id != ""

    def test_jsonl_persistence(self) -> None:
        p = _tmp_path() / "dlq.jsonl"
        dlq = DeadLetterQueue(persistence_path=p)
        dlq.enqueue({"id": "p1"}, "persist test", "consumer-z")

        dlq2 = DeadLetterQueue(persistence_path=p)
        assert dlq2.count() == 1
        entries = dlq2.all_entries()
        assert entries[0].reason == "persist test"

    def test_jsonl_format_is_valid(self) -> None:
        p = _tmp_path() / "dlq2.jsonl"
        dlq = DeadLetterQueue(persistence_path=p)
        dlq.enqueue({"id": "fmt"}, "format test")
        lines = p.read_text().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert "dlq_id" in parsed
        assert "reason" in parsed

    def test_drain_updates_persistence(self) -> None:
        p = _tmp_path() / "dlq3.jsonl"
        dlq = DeadLetterQueue(persistence_path=p)
        dlq.enqueue({"id": "d1"}, "r1")
        dlq.enqueue({"id": "d2"}, "r2")
        dlq.drain(max=1)
        dlq2 = DeadLetterQueue(persistence_path=p)
        assert dlq2.count() == 1


# ===========================================================================
# TestRecoveryAgent
# ===========================================================================


class TestRecoveryAgent:
    def test_no_stuck_sagas_initially(self) -> None:
        coord = TransactionCoordinator()
        agent = RecoveryAgent()
        # New saga, just begun — with a very long timeout it should NOT be stuck
        coord.begin("e-fresh", {})
        stuck = agent.scan(coord, timeout_seconds=9999.0)
        assert stuck == []

    def test_stuck_saga_detected(self) -> None:
        coord = TransactionCoordinator()
        agent = RecoveryAgent()
        saga_id = coord.begin("e-stuck", {"x": 1})
        # Force the updated_at to be in the past
        saga = coord.get(saga_id)
        assert saga is not None
        saga.updated_at = "2000-01-01T00:00:00+00:00"
        # Flush manually — re-insert with old timestamp
        coord._sagas[saga_id] = saga  # type: ignore[attr-defined]

        stuck = agent.scan(coord, timeout_seconds=60.0)
        assert saga_id in stuck

    def test_recovery_sets_compensating(self) -> None:
        coord = TransactionCoordinator()
        dlq = DeadLetterQueue()
        agent = RecoveryAgent()

        saga_id = coord.begin("e-recover", {"amount": 99})
        agent.recover(saga_id, coord, dlq)

        saga = coord.get(saga_id)
        assert saga is not None
        assert saga.state == SagaState.COMPENSATING

    def test_recovery_enqueues_to_dlq(self) -> None:
        coord = TransactionCoordinator()
        dlq = DeadLetterQueue()
        agent = RecoveryAgent()

        saga_id = coord.begin("e-dlq", {"amount": 77})
        agent.recover(saga_id, coord, dlq)

        assert dlq.count() == 1
        entries = dlq.all_entries()
        assert entries[0].source_consumer == "RecoveryAgent"

    def test_recovery_skips_completed_saga(self) -> None:
        coord = TransactionCoordinator()
        dlq = DeadLetterQueue()
        agent = RecoveryAgent()

        saga_id = coord.begin("e-completed", {})
        for step in ("kafka_publish", "warehouse_ack", "notification_ack", "complete"):
            coord.advance(saga_id, step)

        agent.recover(saga_id, coord, dlq)
        assert dlq.count() == 0  # no DLQ entry for already-completed saga

    def test_recover_unknown_saga_raises(self) -> None:
        coord = TransactionCoordinator()
        dlq = DeadLetterQueue()
        agent = RecoveryAgent()
        with pytest.raises(KeyError):
            agent.recover("nonexistent", coord, dlq)


# ===========================================================================
# TestProperties (Hypothesis)
# ===========================================================================


class TestProperties:
    @given(
        event_ids=st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
                ),
            ),
            min_size=1,
            max_size=20,
            unique=True,
        )
    )
    @settings(max_examples=50)
    def test_idempotency_no_double_processing(self, event_ids: list[str]) -> None:
        """Processing the same event_id twice never double-processes it."""
        idem = IdempotencyLog()
        pipeline = ExactlyOncePipeline(idempotency_log=idem)

        for eid in event_ids:
            r1 = pipeline.process({"event_id": eid, "v": 1})
            assert not r1.skipped_duplicate

            r2 = pipeline.process({"event_id": eid, "v": 2})
            assert r2.skipped_duplicate

        # Total seen == number of unique event_ids
        assert idem.count() == len(event_ids)

    @given(
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=30)
    def test_completed_sagas_have_all_steps(self, n: int) -> None:
        """All completed sagas have all 4 pipeline steps acknowledged."""
        coord = TransactionCoordinator()
        pipeline = ExactlyOncePipeline(coordinator=coord)

        saga_ids: list[str] = []
        for i in range(n):
            result = pipeline.process({"event_id": f"prop-{i}", "n": n})
            if result.saga_id is not None:
                saga_ids.append(result.saga_id)

        for sid in saga_ids:
            saga = coord.get(sid)
            assert saga is not None
            assert saga.state == SagaState.COMPLETED
            # Verify all 4 advancement steps are present
            expected_steps = {"kafka_publish", "warehouse_ack", "notification_ack", "complete"}
            assert expected_steps.issubset(set(saga.steps))

    @given(
        payloads=st.lists(
            st.fixed_dictionaries({"amount": st.integers(min_value=0, max_value=10_000)}),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=30)
    def test_outbox_all_entries_published(self, payloads: list[dict[str, int]]) -> None:
        """After processing, every event should have a PUBLISHED outbox entry."""
        outbox = OutboxStore()
        pipeline = ExactlyOncePipeline(outbox=outbox)

        for i, p in enumerate(payloads):
            event: dict[str, object] = {"event_id": f"ob-{i}", **p}
            pipeline.process(event)

        for entry in outbox.all_entries():
            assert entry.status == "PUBLISHED"
