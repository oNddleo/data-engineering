"""DeadLetter + classifier tests."""

from __future__ import annotations

import pytest

from dlq.schema import DeadLetter, FailureKind, classify


def _dl(**overrides: object) -> DeadLetter:
    fields: dict[str, object] = {
        "message_id": "m-001",
        "payload": "{}",
        "original_topic": "orders",
        "failure_kind": FailureKind.UNKNOWN,
        "error_message": "oops",
        "retry_count": 1,
        "first_failed_at_ms": 1_700_000_000_000,
        "last_failed_at_ms": 1_700_000_001_000,
    }
    fields.update(overrides)
    return DeadLetter(**fields)  # type: ignore[arg-type]


def test_basic_construction() -> None:
    dl = _dl()
    assert dl.message_id == "m-001"
    assert dl.headers == {}


def test_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        _dl(message_id="")


def test_rejects_empty_topic() -> None:
    with pytest.raises(ValueError):
        _dl(original_topic="")


def test_rejects_negative_retry() -> None:
    with pytest.raises(ValueError):
        _dl(retry_count=-1)


def test_rejects_negative_timestamp() -> None:
    with pytest.raises(ValueError):
        _dl(first_failed_at_ms=-1)


def test_rejects_last_before_first() -> None:
    with pytest.raises(ValueError):
        _dl(first_failed_at_ms=1000, last_failed_at_ms=500)


@pytest.mark.parametrize(
    ("err", "kind"),
    [
        ("malformed JSON: missing brace", FailureKind.POISON),
        ("decode error at offset 1024", FailureKind.POISON),
        ("429 Too Many Requests", FailureKind.THROTTLED),
        ("throttled by gateway", FailureKind.THROTTLED),
        ("rate limit exceeded", FailureKind.THROTTLED),
        ("timeout after 30s", FailureKind.TIMEOUT),
        ("deadline exceeded", FailureKind.TIMEOUT),
        ("Connection refused: db:5432", FailureKind.TRANSIENT),
        ("503 Service Unavailable", FailureKind.TRANSIENT),
        ("502 Bad Gateway", FailureKind.TRANSIENT),
        ("Unknown signal SIGUSR2", FailureKind.UNKNOWN),
        ("", FailureKind.UNKNOWN),
    ],
)
def test_classify_basic(err: str, kind: FailureKind) -> None:
    assert classify(err) == kind


def test_classify_case_insensitive() -> None:
    assert classify("MALFORMED INPUT") == FailureKind.POISON


def test_age_non_negative() -> None:
    # first_failed_at is far in the past so age is positive.
    dl = _dl(first_failed_at_ms=1_700_000_000_000)
    assert dl.age_ms >= 0
