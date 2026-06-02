"""Schema + fingerprint."""

from __future__ import annotations

import pytest

from idempotency.schema import EntryStatus, IdempotencyEntry, fingerprint


def test_fingerprint_stable() -> None:
    """Same payload → same fingerprint, across calls."""
    assert fingerprint("hello") == fingerprint("hello")


def test_fingerprint_differs_on_different_payload() -> None:
    assert fingerprint("hello") != fingerprint("world")


def test_fingerprint_length() -> None:
    assert len(fingerprint("anything")) == 16


def test_fingerprint_hex() -> None:
    fp = fingerprint("anything")
    assert all(c in "0123456789abcdef" for c in fp)


def test_entry_basic() -> None:
    e = IdempotencyEntry(
        key="k",
        request_fingerprint="abc",
        status=EntryStatus.SUCCEEDED,
        response_body="ok",
        created_at_ms=1000,
        expires_at_ms=2000,
    )
    assert e.key == "k"


def test_entry_rejects_empty_key() -> None:
    with pytest.raises(ValueError):
        IdempotencyEntry(
            key="",
            request_fingerprint="abc",
            status=EntryStatus.SUCCEEDED,
            response_body="ok",
            created_at_ms=0,
            expires_at_ms=1,
        )


def test_entry_rejects_empty_fingerprint() -> None:
    with pytest.raises(ValueError):
        IdempotencyEntry(
            key="k",
            request_fingerprint="",
            status=EntryStatus.SUCCEEDED,
            response_body="ok",
            created_at_ms=0,
            expires_at_ms=1,
        )


def test_entry_rejects_negative_created() -> None:
    with pytest.raises(ValueError):
        IdempotencyEntry(
            key="k",
            request_fingerprint="f",
            status=EntryStatus.SUCCEEDED,
            response_body="ok",
            created_at_ms=-1,
            expires_at_ms=10,
        )


def test_entry_rejects_expires_le_created() -> None:
    with pytest.raises(ValueError):
        IdempotencyEntry(
            key="k",
            request_fingerprint="f",
            status=EntryStatus.SUCCEEDED,
            response_body="ok",
            created_at_ms=100,
            expires_at_ms=100,
        )


def test_in_progress_must_have_empty_body() -> None:
    with pytest.raises(ValueError):
        IdempotencyEntry(
            key="k",
            request_fingerprint="f",
            status=EntryStatus.IN_PROGRESS,
            response_body="oops",  # forbidden
            created_at_ms=0,
            expires_at_ms=10,
        )
