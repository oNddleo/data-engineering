"""Schema invariants for Transaction + Channel."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from n247mon.schema import VN_TZ, Channel

from ._fixtures import make_txn


def test_channel_values():
    assert {c.value for c in Channel} == {"MOBILE_APP", "INTERNET_BANKING", "ATM", "BRANCH"}


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_transaction_happy_path():
    t = make_txn(amount=2_000_000)
    assert t.amount_vnd == 2_000_000
    assert t.channel is Channel.MOBILE_APP


def test_transaction_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        make_txn(amount=0)
    with pytest.raises(ValueError):
        make_txn(amount=-1)


def test_transaction_rejects_empty_txn_id():
    with pytest.raises(ValueError):
        make_txn(txn_id="")


def test_transaction_rejects_empty_accounts():
    with pytest.raises(ValueError):
        make_txn(initiator="")
    with pytest.raises(ValueError):
        make_txn(beneficiary="")


def test_transaction_rejects_bad_bin():
    with pytest.raises(ValueError):
        make_txn(initiator_bin="ABCDEF")
    with pytest.raises(ValueError):
        make_txn(beneficiary_bin="12345")  # 5 digits


def test_transaction_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_txn(occurred_at=datetime(2026, 5, 14, 9, 0))


def test_transaction_accepts_utc_aware_datetime():
    t = make_txn(occurred_at=datetime(2026, 5, 14, 2, 0, tzinfo=timezone.utc))
    assert t.occurred_at.tzinfo is not None


def test_transaction_frozen():
    t = make_txn()
    with pytest.raises((AttributeError, TypeError)):
        t.amount_vnd = 999  # type: ignore[misc]
