"""Daily summary aggregation."""

from __future__ import annotations

from datetime import datetime

from vnbank.schema import VN_TZ, TxnDirection, TxnKind, TxnStatus
from vnbank.summary import aggregate_daily

from ._fixtures import make_txn


def test_aggregate_groups_per_account_per_day() -> None:
    txns = [
        make_txn(txn_id="T-1", amount_vnd=100_000),
        make_txn(txn_id="T-2", amount_vnd=200_000),
    ]
    summaries = aggregate_daily(txns)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.n_txns == 2
    assert s.total_debit_vnd == 300_000


def test_aggregate_splits_by_day() -> None:
    txns = [
        make_txn(
            txn_id="T-1",
            amount_vnd=100_000,
            occurred_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
        ),
        make_txn(
            txn_id="T-2",
            amount_vnd=200_000,
            occurred_at=datetime(2026, 5, 19, 10, 0, tzinfo=VN_TZ),
        ),
    ]
    summaries = aggregate_daily(txns)
    assert len(summaries) == 2
    assert {s.date for s in summaries} == {"2026-05-18", "2026-05-19"}


def test_aggregate_splits_credits_debits() -> None:
    txns = [
        make_txn(
            txn_id="T-1",
            amount_vnd=100_000,
            direction=TxnDirection.DEBIT,
        ),
        make_txn(
            txn_id="T-2",
            amount_vnd=500_000,
            direction=TxnDirection.CREDIT,
        ),
    ]
    s = aggregate_daily(txns)[0]
    assert s.total_debit_vnd == 100_000
    assert s.total_credit_vnd == 500_000
    assert s.net_flow_vnd == 400_000


def test_aggregate_counts_cash_separately() -> None:
    txns = [
        make_txn(
            txn_id="T-1",
            kind=TxnKind.CASH_DEPOSIT,
            direction=TxnDirection.CREDIT,
            amount_vnd=10_000_000,
        ),
        make_txn(
            txn_id="T-2",
            kind=TxnKind.CASH_WITHDRAWAL,
            direction=TxnDirection.DEBIT,
            amount_vnd=3_000_000,
        ),
    ]
    s = aggregate_daily(txns)[0]
    assert s.n_cash_deposits == 1
    assert s.cash_deposit_amount_vnd == 10_000_000
    assert s.n_cash_withdrawals == 1
    assert s.cash_withdrawal_amount_vnd == 3_000_000


def test_aggregate_excludes_rejected() -> None:
    txns = [
        make_txn(txn_id="T-1", amount_vnd=100_000),
        make_txn(txn_id="T-2", amount_vnd=999_000, status=TxnStatus.REJECTED),
    ]
    s = aggregate_daily(txns)[0]
    assert s.n_txns == 1  # rejected didn't count


def test_aggregate_excludes_reversed_from_totals_but_counts() -> None:
    txns = [
        make_txn(txn_id="T-1", amount_vnd=100_000),
        make_txn(
            txn_id="T-2",
            amount_vnd=500_000,
            status=TxnStatus.REVERSED,
        ),
    ]
    s = aggregate_daily(txns)[0]
    assert s.n_txns == 2  # reversed counted in n_txns
    assert s.total_debit_vnd == 100_000  # but excluded from totals


def test_aggregate_sorted_by_date_then_account() -> None:
    txns = [
        make_txn(
            txn_id="T-1",
            account_number="222",
            occurred_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
        ),
        make_txn(
            txn_id="T-2",
            account_number="111",
            occurred_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
        ),
    ]
    summaries = aggregate_daily(txns)
    assert [s.account_number for s in summaries] == ["111", "222"]


def test_aggregate_empty() -> None:
    assert aggregate_daily([]) == []
