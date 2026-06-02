"""Schema invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from fraudvn.schema import VN_TZ, Channel, Decision, FraudDecision, SignalHit

from ._fixtures import make_req


def test_decision_enum_values():
    assert {d.value for d in Decision} == {"ALLOW", "REVIEW", "BLOCK"}


def test_channel_enum_values():
    assert "MOBILE_APP" in {c.value for c in Channel}


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_req_happy_path():
    r = make_req()
    assert r.amount_vnd == 1_000_000


def test_req_rejects_empty_id():
    with pytest.raises(ValueError):
        make_req(txn_id="")


def test_req_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        make_req(amount=0)
    with pytest.raises(ValueError):
        make_req(amount=-1)


def test_req_rejects_empty_accounts():
    with pytest.raises(ValueError):
        make_req(initiator="")
    with pytest.raises(ValueError):
        make_req(beneficiary="")


def test_req_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_req(occurred_at=datetime(2026, 5, 14, 14, 0))


def test_req_otp_pair_must_be_both_set_or_both_none():
    base = datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ)
    from fraudvn.schema import TransactionRequest

    with pytest.raises(ValueError):
        TransactionRequest(
            txn_id="T",
            initiator_account="A",
            beneficiary_account="B",
            beneficiary_bank_bin="970418",
            amount_vnd=100,
            narrative="x",
            channel=Channel.MOBILE_APP,
            occurred_at=base,
            otp_issued_at=base,
            otp_verified_at=None,
        )


def test_req_otp_verified_cannot_precede_issued():
    base = datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ)
    from fraudvn.schema import TransactionRequest

    with pytest.raises(ValueError):
        TransactionRequest(
            txn_id="T",
            initiator_account="A",
            beneficiary_account="B",
            beneficiary_bank_bin="970418",
            amount_vnd=100,
            narrative="x",
            channel=Channel.MOBILE_APP,
            occurred_at=base,
            otp_issued_at=base,
            otp_verified_at=base - timedelta(seconds=5),
        )


def test_signal_hit_construction():
    s = SignalHit(name="X", points=42, detail="x")
    assert s.points == 42


def test_fraud_decision_has_signal_helper():
    d = FraudDecision(
        txn_id="T",
        decision=Decision.REVIEW,
        score=60,
        signals=(
            SignalHit(name="A", points=30, detail=""),
            SignalHit(name="B", points=30, detail=""),
        ),
    )
    assert d.has_signal("A")
    assert not d.has_signal("C")
