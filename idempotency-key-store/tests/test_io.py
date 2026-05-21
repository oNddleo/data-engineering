"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from idempotency.io_jsonl import dump, from_dict, load, to_dict
from idempotency.schema import EntryStatus, IdempotencyEntry


def _sample() -> IdempotencyEntry:
    return IdempotencyEntry(
        key="k-001",
        request_fingerprint="abcdef0123456789",
        status=EntryStatus.SUCCEEDED,
        response_body='{"ok":true}',
        created_at_ms=1_700_000_000_000,
        expires_at_ms=1_700_000_010_000,
    )


def test_roundtrip() -> None:
    e = _sample()
    assert from_dict(to_dict(e)) == e


def test_dump_load() -> None:
    assert load(dump([_sample()])) == [_sample()]


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
