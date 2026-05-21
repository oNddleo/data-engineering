"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from dlq.io_jsonl import dump, from_dict, load, to_dict
from dlq.schema import DeadLetter, FailureKind


def _dl() -> DeadLetter:
    return DeadLetter(
        message_id="m-001",
        payload='{"i":1}',
        original_topic="orders",
        failure_kind=FailureKind.TRANSIENT,
        error_message="503 Service Unavailable",
        retry_count=3,
        first_failed_at_ms=1_700_000_000_000,
        last_failed_at_ms=1_700_000_003_000,
        headers={"trace_id": "abc-123", "source": "test"},
    )


def test_roundtrip() -> None:
    dl = _dl()
    assert from_dict(to_dict(dl)) == dl


def test_dump_load() -> None:
    assert load(dump([_dl()])) == [_dl()]


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")


def test_load_rejects_bad_headers() -> None:
    with pytest.raises(TypeError):
        load(
            '{"message_id":"m","payload":"{}","original_topic":"t","failure_kind":"transient",'
            '"error_message":"x","retry_count":0,"first_failed_at_ms":0,"last_failed_at_ms":0,'
            '"headers":{"k":1}}\n'
        )
