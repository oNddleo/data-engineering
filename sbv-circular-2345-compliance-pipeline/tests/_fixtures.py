"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from sbv2345.schema import (
    VN_TZ,
    AuditEvent,
    AuthMethod,
    BiometricMethod,
    Channel,
    TransactionEvent,
    TriggerKind,
)


def make_txn(
    *,
    txn_id: str = "T-1",
    initiator: str = "0000000001",
    beneficiary: str = "0000000002",
    amount: int = 1_000_000,
    channel: Channel = Channel.MOBILE_APP,
    occurred_at: datetime | None = None,
    auth_method: AuthMethod = AuthMethod.PIN,
    biometric_method: BiometricMethod | None = None,
    cross_border: bool = False,
    initiator_bank_bin: str = "970418",
    beneficiary_bank_bin: str = "970436",
) -> TransactionEvent:
    return TransactionEvent(
        txn_id=txn_id,
        initiator_account=initiator,
        beneficiary_account=beneficiary,
        amount_vnd=amount,
        channel=channel,
        occurred_at=occurred_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
        auth_method=auth_method,
        biometric_method=biometric_method,
        cross_border=cross_border,
        initiator_bank_bin=initiator_bank_bin,
        beneficiary_bank_bin=beneficiary_bank_bin,
    )


def make_audit_event(
    *,
    txn: TransactionEvent | None = None,
    triggers: tuple[TriggerKind, ...] = (TriggerKind.SINGLE_TXN_OVER_10M,),
    daily_total: int = 15_000_000,
) -> AuditEvent:
    return AuditEvent(
        txn=txn or make_txn(amount=15_000_000),
        triggered_kinds=triggers,
        legal_bases=tuple("QĐ 2345/QĐ-NHNN" for _ in triggers),
        daily_cumulative_after_vnd=daily_total,
    )


def t_at(seconds: int) -> datetime:
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(seconds=seconds)


__all__ = ["make_audit_event", "make_txn", "t_at"]
