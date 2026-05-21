"""DeadLetterQueue mutation + replay."""

from __future__ import annotations

from dlq.queue import DeadLetterQueue
from dlq.schema import DeadLetter, FailureKind


def _dl(
    mid: str = "m",
    kind: FailureKind = FailureKind.TRANSIENT,
    topic: str = "orders",
    first: int = 1_700_000_000_000,
) -> DeadLetter:
    return DeadLetter(
        message_id=mid,
        payload="{}",
        original_topic=topic,
        failure_kind=kind,
        error_message="x",
        retry_count=1,
        first_failed_at_ms=first,
        last_failed_at_ms=first + 100,
    )


def test_append_and_len() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="a"))
    q.append(_dl(mid="b"))
    assert len(q) == 2


def test_iter() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="a"))
    q.append(_dl(mid="b"))
    assert [dl.message_id for dl in q] == ["a", "b"]


def test_filter_by_kind() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="a", kind=FailureKind.POISON))
    q.append(_dl(mid="b", kind=FailureKind.TRANSIENT))
    q.append(_dl(mid="c", kind=FailureKind.TRANSIENT))
    assert {dl.message_id for dl in q.filter(kind=FailureKind.TRANSIENT)} == {"b", "c"}


def test_filter_by_topic() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="a", topic="orders"))
    q.append(_dl(mid="b", topic="payments"))
    assert {dl.message_id for dl in q.filter(topic="orders")} == {"a"}


def test_counts_by_kind() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="a", kind=FailureKind.POISON))
    q.append(_dl(mid="b", kind=FailureKind.TRANSIENT))
    q.append(_dl(mid="c", kind=FailureKind.TRANSIENT))
    counts = q.counts_by_kind()
    assert counts[FailureKind.POISON] == 1
    assert counts[FailureKind.TRANSIENT] == 2
    assert counts[FailureKind.UNKNOWN] == 0


def test_clear() -> None:
    q = DeadLetterQueue()
    q.append(_dl())
    q.clear()
    assert len(q) == 0


def test_replay_all_succeed() -> None:
    q = DeadLetterQueue()
    q.extend([_dl(mid=f"m{i}") for i in range(5)])
    result = q.replay(handler=lambda _: True)
    assert result.n_replayed == 5
    assert result.n_succeeded == 5
    assert result.n_remaining == 0
    assert len(q) == 0


def test_replay_all_fail() -> None:
    q = DeadLetterQueue()
    q.extend([_dl(mid=f"m{i}") for i in range(5)])
    result = q.replay(handler=lambda _: False)
    assert result.n_replayed == 5
    assert result.n_succeeded == 0
    assert result.n_remaining == 5
    assert len(q) == 5


def test_replay_filtered_by_kind() -> None:
    q = DeadLetterQueue()
    q.append(_dl(mid="poison", kind=FailureKind.POISON))
    q.append(_dl(mid="transient", kind=FailureKind.TRANSIENT))
    # Only replay TRANSIENT; POISON should be left in place untouched.
    result = q.replay(handler=lambda _: True, kind=FailureKind.TRANSIENT)
    assert result.n_replayed == 1
    assert len(q) == 1
    assert next(iter(q)).message_id == "poison"


def test_replay_success_rate() -> None:
    from dlq.queue import ReplayResult

    r = ReplayResult(n_replayed=4, n_succeeded=3, n_remaining=1)
    assert r.success_rate == 0.75
    empty = ReplayResult(n_replayed=0, n_succeeded=0, n_remaining=0)
    assert empty.success_rate == 0.0
