"""IdempotencyStore behaviour."""

from __future__ import annotations

import pytest

from idempotency.schema import EntryStatus
from idempotency.store import IdempotencyStore, Outcome


def test_new_key_reserved() -> None:
    s = IdempotencyStore()
    r = s.check_or_reserve("k1", "fp1", now_ms=0, ttl_ms=10_000)
    assert r.outcome == Outcome.NEW
    assert r.entry is not None
    assert r.entry.status == EntryStatus.IN_PROGRESS


def test_in_progress_second_call() -> None:
    """Calling again with the same payload while in-progress returns IN_PROGRESS."""
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0)
    r = s.check_or_reserve("k1", "fp1", now_ms=1)
    assert r.outcome == Outcome.IN_PROGRESS


def test_replay_after_finalize_success() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0)
    s.finalize("k1", '{"ok":true}', EntryStatus.SUCCEEDED, now_ms=1)
    r = s.check_or_reserve("k1", "fp1", now_ms=2)
    assert r.outcome == Outcome.REPLAY_SUCCESS
    assert r.entry is not None
    assert r.entry.response_body == '{"ok":true}'


def test_replay_failed_after_failure() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0)
    s.finalize("k1", "", EntryStatus.FAILED, now_ms=1)
    r = s.check_or_reserve("k1", "fp1", now_ms=2)
    assert r.outcome == Outcome.REPLAY_FAILED


def test_conflict_on_different_fingerprint() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0)
    r = s.check_or_reserve("k1", "fp_DIFFERENT", now_ms=1)
    assert r.outcome == Outcome.CONFLICT


def test_ttl_expiry_returns_new() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0, ttl_ms=100)
    s.finalize("k1", '{"ok":true}', EntryStatus.SUCCEEDED, now_ms=10)
    # After TTL, the entry is gone — caller can reserve fresh.
    r = s.check_or_reserve("k1", "fp1", now_ms=10_000)
    assert r.outcome == Outcome.NEW


def test_finalize_without_reservation_raises() -> None:
    s = IdempotencyStore()
    with pytest.raises(KeyError):
        s.finalize("missing", "", EntryStatus.SUCCEEDED, now_ms=0)


def test_finalize_in_progress_rejected() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k", "fp", now_ms=0)
    with pytest.raises(ValueError):
        s.finalize("k", "", EntryStatus.IN_PROGRESS, now_ms=1)


def test_failed_finalize_clears_body() -> None:
    """A FAILED finalize shouldn't carry a fake response body."""
    s = IdempotencyStore()
    s.check_or_reserve("k", "fp", now_ms=0)
    entry = s.finalize("k", "nope", EntryStatus.FAILED, now_ms=1)
    assert entry.response_body == ""


def test_get_respects_ttl() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k", "fp", now_ms=0, ttl_ms=100)
    s.finalize("k", "ok", EntryStatus.SUCCEEDED, now_ms=10)
    assert s.get("k", now_ms=50) is not None
    assert s.get("k", now_ms=200) is None


def test_evict_expired() -> None:
    s = IdempotencyStore()
    s.check_or_reserve("k1", "fp1", now_ms=0, ttl_ms=100)
    s.check_or_reserve("k2", "fp2", now_ms=0, ttl_ms=1_000)
    n = s.evict_expired(now_ms=500)
    assert n == 1
    assert len(s) == 1


def test_ttl_ms_validation() -> None:
    s = IdempotencyStore()
    with pytest.raises(ValueError):
        s.check_or_reserve("k", "fp", now_ms=0, ttl_ms=0)
    with pytest.raises(ValueError):
        s.check_or_reserve("k", "fp", now_ms=0, ttl_ms=-1)


def test_len_grows_with_reservations() -> None:
    s = IdempotencyStore()
    assert len(s) == 0
    s.check_or_reserve("a", "fp", now_ms=0)
    s.check_or_reserve("b", "fp", now_ms=0)
    assert len(s) == 2
