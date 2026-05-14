"""Schema invariants."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sbv2345.schema import (
    VN_TZ,
    AuditEvent,
    AuthMethod,
    BiometricMethod,
    Channel,
    TriggerKind,
)

from ._fixtures import make_audit_event, make_txn


def test_enum_values_complete():
    assert {c.value for c in Channel} == {"MOBILE_APP", "INTERNET_BANKING", "ATM", "BRANCH"}
    assert {a.value for a in AuthMethod} == {"PIN", "OTP", "BIOMETRIC", "NONE"}
    assert {b.value for b in BiometricMethod} == {"FACE", "FINGERPRINT", "VOICE", "IRIS"}
    assert {t.value for t in TriggerKind} == {
        "SINGLE_TXN_OVER_10M",
        "DAILY_CUMULATIVE_OVER_20M",
        "HIGH_RISK_BENEFICIARY",
        "INTERNATIONAL_TRANSFER",
    }


def test_vn_tz_offset_is_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_txn_happy_path():
    t = make_txn()
    assert t.amount_vnd == 1_000_000
    assert t.channel is Channel.MOBILE_APP


def test_txn_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        make_txn(amount=0)
    with pytest.raises(ValueError):
        make_txn(amount=-1)


def test_txn_rejects_empty_accounts():
    with pytest.raises(ValueError):
        make_txn(initiator="")
    with pytest.raises(ValueError):
        make_txn(beneficiary="")


def test_txn_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_txn(occurred_at=datetime(2026, 5, 14))


def test_txn_accepts_utc_aware_datetime():
    t = make_txn(occurred_at=datetime(2026, 5, 14, 2, 0, tzinfo=timezone.utc))
    assert t.occurred_at.tzinfo is not None


def test_txn_biometric_requires_method():
    with pytest.raises(ValueError):
        make_txn(auth_method=AuthMethod.BIOMETRIC, biometric_method=None)


def test_txn_non_biometric_rejects_method():
    with pytest.raises(ValueError):
        make_txn(auth_method=AuthMethod.PIN, biometric_method=BiometricMethod.FACE)


def test_txn_biometric_with_method_ok():
    t = make_txn(auth_method=AuthMethod.BIOMETRIC, biometric_method=BiometricMethod.FACE)
    assert t.biometric_method is BiometricMethod.FACE


def test_audit_event_requires_at_least_one_trigger():
    with pytest.raises(ValueError):
        AuditEvent(txn=make_txn(amount=15_000_000), triggered_kinds=())


def test_audit_event_rejects_duplicate_triggers():
    with pytest.raises(ValueError):
        AuditEvent(
            txn=make_txn(amount=15_000_000),
            triggered_kinds=(TriggerKind.SINGLE_TXN_OVER_10M, TriggerKind.SINGLE_TXN_OVER_10M),
        )


def test_audit_event_legal_bases_must_be_parallel_when_supplied():
    with pytest.raises(ValueError):
        AuditEvent(
            txn=make_txn(amount=15_000_000),
            triggered_kinds=(TriggerKind.SINGLE_TXN_OVER_10M,),
            legal_bases=("a", "b"),  # two but only one trigger
        )


def test_audit_event_legal_bases_empty_ok():
    """Empty legal_bases means caller didn't fill them in — accepted."""
    e = AuditEvent(
        txn=make_txn(amount=15_000_000), triggered_kinds=(TriggerKind.SINGLE_TXN_OVER_10M,)
    )
    assert e.legal_bases == ()


def test_audit_event_helper_factory():
    e = make_audit_event()
    assert e.triggered_kinds == (TriggerKind.SINGLE_TXN_OVER_10M,)
