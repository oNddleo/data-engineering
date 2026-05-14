"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from amlgraph.schema import VN_TZ, AccountType, Channel, RiskFlag

from ._fixtures import make_account, make_txn


def test_enum_values():
    assert {t.value for t in AccountType} == {
        "PERSONAL",
        "BUSINESS",
        "GOVERNMENT",
        "SHELL",
        "UNKNOWN",
    }
    assert "MOBILE_APP" in {c.value for c in Channel}
    assert "PEP" in {r.value for r in RiskFlag}


def test_vn_tz_offset_is_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_account_happy_path():
    a = make_account(risk_flags=(RiskFlag.PEP,))
    assert a.bank_bin == "970418"
    assert RiskFlag.PEP in a.risk_flags


def test_account_rejects_empty_id():
    with pytest.raises(ValueError):
        make_account(account_id="")


def test_account_rejects_bad_bin():
    with pytest.raises(ValueError):
        make_account(bank_bin="ABCDEF")
    with pytest.raises(ValueError):
        make_account(bank_bin="12345")


def test_account_rejects_duplicate_risk_flags():
    with pytest.raises(ValueError):
        make_account(risk_flags=(RiskFlag.PEP, RiskFlag.PEP))


def test_txn_happy_path():
    t = make_txn(amount=2_000_000)
    assert t.amount_vnd == 2_000_000


def test_txn_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        make_txn(amount=0)


def test_txn_rejects_self_loop():
    with pytest.raises(ValueError):
        make_txn(src="ACC-1", dst="ACC-1")


def test_txn_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_txn(occurred_at=datetime(2026, 5, 14))


def test_txn_rejects_empty_accounts():
    with pytest.raises(ValueError):
        make_txn(src="")
    with pytest.raises(ValueError):
        make_txn(dst="")
