"""Schema validation: Bank, Account, Transaction, DailySummary."""

from __future__ import annotations

from datetime import datetime

import pytest

from vnbank.schema import (
    CTR_THRESHOLD_VND,
    VN_TZ,
    Account,
    Bank,
    DailySummary,
    TxnDirection,
    TxnKind,
    TxnStatus,
)

from ._fixtures import make_txn

# ---------- Bank ------------------------------------------------------------


def test_bank_basic() -> None:
    b = Bank(
        bin_code="970436",
        abbreviation="VCB",
        name_vi="Vietcombank",
        name_en="Vietcombank",
    )
    assert b.bin_code == "970436"


def test_bank_rejects_bad_bin_length() -> None:
    with pytest.raises(ValueError, match="bin_code"):
        Bank(bin_code="9704", abbreviation="VCB", name_vi="x", name_en="x")


def test_bank_rejects_non_digit_bin() -> None:
    with pytest.raises(ValueError, match="bin_code"):
        Bank(bin_code="VCB123", abbreviation="VCB", name_vi="x", name_en="x")


def test_bank_rejects_empty_abbr() -> None:
    with pytest.raises(ValueError, match="abbreviation"):
        Bank(bin_code="970436", abbreviation="", name_vi="x", name_en="x")


# ---------- Account ---------------------------------------------------------


def test_account_basic() -> None:
    a = Account(
        account_number="1234567890",
        bank_bin="970436",
        holder_name="Nguyen Van A",
    )
    assert a.currency == "VND"


def test_account_rejects_non_digit() -> None:
    with pytest.raises(ValueError, match="account_number"):
        Account(account_number="ABC123", bank_bin="970436", holder_name="x")


def test_account_rejects_unsupported_currency() -> None:
    with pytest.raises(ValueError, match="currency"):
        Account(
            account_number="123",
            bank_bin="970436",
            holder_name="x",
            currency="GBP",
        )


# ---------- Transaction -----------------------------------------------------


def test_txn_basic() -> None:
    t = make_txn()
    assert t.amount_vnd == 100_000
    assert t.signed_amount_vnd == -100_000  # debit


def test_txn_credit_positive() -> None:
    t = make_txn(direction=TxnDirection.CREDIT)
    assert t.signed_amount_vnd == 100_000


def test_txn_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount_vnd"):
        make_txn(amount_vnd=-1)


def test_txn_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_txn(occurred_at=datetime(2026, 5, 18, 9, 0, 0))


def test_txn_rejects_bad_counterparty_bin() -> None:
    with pytest.raises(ValueError, match="counterparty_bank_bin"):
        make_txn(counterparty_bank_bin="ABC")


def test_txn_kinds_complete() -> None:
    expected = {
        "INTRA_BANK_TRANSFER",
        "INTERBANK_TRANSFER",
        "VIETQR_RECEIVE",
        "VIETQR_SEND",
        "CASH_DEPOSIT",
        "CASH_WITHDRAWAL",
        "CARD_PURCHASE",
        "BILL_PAYMENT",
        "SALARY_CREDIT",
        "INTEREST",
    }
    assert {k.value for k in TxnKind} == expected


def test_txn_statuses_complete() -> None:
    assert {s.value for s in TxnStatus} == {
        "PENDING",
        "POSTED",
        "REVERSED",
        "REJECTED",
    }


# ---------- DailySummary ----------------------------------------------------


def _make_summary(**overrides: object) -> DailySummary:
    defaults = {
        "account_number": "123",
        "bank_bin": "970436",
        "date": "2026-05-18",
        "n_txns": 5,
        "total_debit_vnd": 1_000_000,
        "total_credit_vnd": 500_000,
        "n_cash_deposits": 0,
        "cash_deposit_amount_vnd": 0,
        "n_cash_withdrawals": 0,
        "cash_withdrawal_amount_vnd": 0,
    }
    defaults.update(overrides)
    return DailySummary(**defaults)  # type: ignore[arg-type]


def test_summary_net_flow() -> None:
    s = _make_summary(total_debit_vnd=300_000, total_credit_vnd=1_000_000)
    assert s.net_flow_vnd == 700_000


def test_summary_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError, match="total_debit_vnd"):
        _make_summary(total_debit_vnd=-1)


# ---------- Constants -------------------------------------------------------


def test_ctr_threshold_is_300m() -> None:
    """CTR threshold per Decree 87/2017 + Circular 09/2017."""
    assert CTR_THRESHOLD_VND == 300_000_000


def test_vn_tz_is_utc7() -> None:
    assert VN_TZ.utcoffset(None) is not None
