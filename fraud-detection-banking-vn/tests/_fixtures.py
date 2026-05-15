"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from fraudvn.schema import VN_TZ, Channel, TransactionRequest


def make_req(
    *,
    txn_id: str = "T-1",
    initiator: str = "ACC-INITIATOR",
    beneficiary: str = "ACC-BENEFICIARY",
    amount: int = 1_000_000,
    narrative: str = "an trua",
    channel: Channel = Channel.MOBILE_APP,
    occurred_at: datetime | None = None,
    otp_delta_seconds: float | None = None,
    bank_bin: str = "970418",
) -> TransactionRequest:
    occurred = occurred_at or datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ)
    otp_issued = None
    otp_verified = None
    if otp_delta_seconds is not None:
        otp_issued = occurred - timedelta(seconds=30)
        otp_verified = otp_issued + timedelta(seconds=otp_delta_seconds)
    return TransactionRequest(
        txn_id=txn_id,
        initiator_account=initiator,
        beneficiary_account=beneficiary,
        beneficiary_bank_bin=bank_bin,
        amount_vnd=amount,
        narrative=narrative,
        channel=channel,
        occurred_at=occurred,
        otp_issued_at=otp_issued,
        otp_verified_at=otp_verified,
    )


def t_at(seconds: int, *, base_hour: int = 14) -> datetime:
    return datetime(2026, 5, 14, base_hour, 0, tzinfo=VN_TZ) + timedelta(seconds=seconds)


__all__ = ["make_req", "t_at"]
