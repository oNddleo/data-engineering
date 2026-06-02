"""Shared test fixtures — small Transaction factory."""

from __future__ import annotations

from datetime import datetime, timedelta

from n247mon.schema import VN_TZ, Channel, Transaction


def make_txn(
    *,
    txn_id: str = "T-1",
    initiator: str = "0010001000",
    initiator_bin: str = "970418",
    beneficiary: str = "0020002000",
    beneficiary_bin: str = "970436",
    amount: int = 1_000_000,
    channel: Channel = Channel.MOBILE_APP,
    occurred_at: datetime | None = None,
    biometric: bool = False,
    device_id: str | None = "dev-test",
    geo_ip: str | None = None,
) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        initiator_account=initiator,
        initiator_bank_bin=initiator_bin,
        beneficiary_account=beneficiary,
        beneficiary_bank_bin=beneficiary_bin,
        amount_vnd=amount,
        channel=channel,
        occurred_at=occurred_at or datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ),
        biometric_verified=biometric,
        device_id=device_id,
        geo_ip=geo_ip,
    )


def t_at(seconds: int) -> datetime:
    """Helper — base time + N seconds."""
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(seconds=seconds)


__all__ = ["make_txn", "t_at"]
