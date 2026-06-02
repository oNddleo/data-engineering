"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from idempotency.schema import EntryStatus, fingerprint
from idempotency.store import IdempotencyStore, Outcome


@given(st.text(min_size=1, max_size=50))
@settings(max_examples=60)
def test_fingerprint_deterministic(payload: str) -> None:
    """Same payload always yields same fingerprint."""
    assert fingerprint(payload) == fingerprint(payload)


@given(
    st.lists(st.text(alphabet="abc", min_size=1, max_size=3), min_size=1, max_size=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_repeated_same_payload_replay(keys: list[str]) -> None:
    """Re-sending the same (key, payload) after finalize always replays."""
    store = IdempotencyStore()
    payload = "p"
    fp = fingerprint(payload)

    # First pass: reserve + finalize each unique key.
    seen: set[str] = set()
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        r = store.check_or_reserve(k, fp, now_ms=0)
        assert r.outcome == Outcome.NEW
        store.finalize(k, "ok", EntryStatus.SUCCEEDED, now_ms=1)

    # Second pass: every retry should REPLAY_SUCCESS.
    for k in keys:
        r = store.check_or_reserve(k, fp, now_ms=2)
        assert r.outcome == Outcome.REPLAY_SUCCESS


@given(
    st.text(alphabet="abc", min_size=1, max_size=5),
    st.text(alphabet="xyz", min_size=1, max_size=10),
    st.text(alphabet="xyz", min_size=1, max_size=10),
)
@settings(max_examples=60)
def test_conflict_on_different_payload(key: str, payload_a: str, payload_b: str) -> None:
    """Same key, different payload → CONFLICT after finalize."""
    if payload_a == payload_b:
        return
    store = IdempotencyStore()
    fp_a = fingerprint(payload_a)
    fp_b = fingerprint(payload_b)
    if fp_a == fp_b:
        return  # SHA collision in 16 hex chars — extremely rare

    store.check_or_reserve(key, fp_a, now_ms=0)
    store.finalize(key, "ok", EntryStatus.SUCCEEDED, now_ms=1)
    r = store.check_or_reserve(key, fp_b, now_ms=2)
    assert r.outcome == Outcome.CONFLICT
