"""Builders for CDRs in tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cdrpipe.schema import CDR, VN_TZ, CDRKind

DEFAULT_TS = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)


def make_cdr(**overrides: Any) -> CDR:
    """Build a CDR with sane defaults — override any field."""
    defaults: dict[str, Any] = {
        "cdr_id": "C-0001",
        "subscriber_msisdn": "0961234567",  # Viettel
        "peer_msisdn": "0911234567",  # VinaPhone
        "kind": CDRKind.VOICE,
        "occurred_at": DEFAULT_TS,
        "duration_seconds": 60,
        "bytes_used": 0,
        "n_messages": 0,
        "is_roaming": False,
        "is_premium": False,
    }
    defaults.update(overrides)
    return CDR(**defaults)


def voice_cdr(
    cdr_id: str = "V-1",
    subscriber: str = "0961234567",
    peer: str = "0911234567",
    duration_seconds: int = 60,
    at: datetime = DEFAULT_TS,
    *,
    is_roaming: bool = False,
    is_premium: bool = False,
) -> CDR:
    return make_cdr(
        cdr_id=cdr_id,
        subscriber_msisdn=subscriber,
        peer_msisdn=peer,
        kind=CDRKind.VOICE,
        occurred_at=at,
        duration_seconds=duration_seconds,
        bytes_used=0,
        n_messages=0,
        is_roaming=is_roaming,
        is_premium=is_premium,
    )


def sms_cdr(
    cdr_id: str = "S-1",
    subscriber: str = "0961234567",
    peer: str = "0911234567",
    at: datetime = DEFAULT_TS,
    *,
    is_roaming: bool = False,
) -> CDR:
    return make_cdr(
        cdr_id=cdr_id,
        subscriber_msisdn=subscriber,
        peer_msisdn=peer,
        kind=CDRKind.SMS,
        occurred_at=at,
        duration_seconds=0,
        bytes_used=0,
        n_messages=1,
        is_roaming=is_roaming,
    )


def data_cdr(
    cdr_id: str = "D-1",
    subscriber: str = "0961234567",
    bytes_used: int = 10 * 1024 * 1024,
    at: datetime = DEFAULT_TS,
    *,
    is_roaming: bool = False,
) -> CDR:
    return make_cdr(
        cdr_id=cdr_id,
        subscriber_msisdn=subscriber,
        peer_msisdn="",
        kind=CDRKind.DATA,
        occurred_at=at,
        duration_seconds=0,
        bytes_used=bytes_used,
        n_messages=0,
        is_roaming=is_roaming,
    )


__all__ = ["DEFAULT_TS", "data_cdr", "make_cdr", "sms_cdr", "voice_cdr"]
