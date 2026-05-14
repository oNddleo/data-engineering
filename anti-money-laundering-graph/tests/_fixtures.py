"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from amlgraph.schema import VN_TZ, Account, AccountType, Channel, Transaction


def make_account(
    *,
    account_id: str = "ACC-1",
    bank_bin: str = "970418",
    account_type: AccountType = AccountType.PERSONAL,
    risk_flags: tuple = (),
) -> Account:
    return Account(
        account_id=account_id,
        bank_bin=bank_bin,
        account_type=account_type,
        risk_flags=risk_flags,
    )


def make_txn(
    *,
    txn_id: str = "T-1",
    src: str = "ACC-1",
    dst: str = "ACC-2",
    amount: int = 1_000_000,
    occurred_at: datetime | None = None,
    channel: Channel = Channel.MOBILE_APP,
) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        from_account=src,
        to_account=dst,
        amount_vnd=amount,
        occurred_at=occurred_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
        channel=channel,
    )


def t_at(seconds: int) -> datetime:
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(seconds=seconds)


__all__ = ["make_account", "make_txn", "t_at"]
