"""VN telecom CDR schema.

Models the CDR (Call Detail Record) format emitted by VN telco core
networks (Viettel, VNPT/VinaPhone, MobiFone, Vietnamobile, Reddi).
Each CDR represents a single billable event:

| Kind     | Tracked metric        | Pricing axis              |
| -------- | --------------------- | ------------------------- |
| ``VOICE``| ``duration_seconds``  | per-minute, peak/off-peak |
| ``SMS``  | ``n_messages = 1``    | per-message, flat         |
| ``DATA`` | ``bytes_used``        | per-MB, prepaid/postpaid  |

All money is **integer VND** (Vietnam doesn't use sub-units in
billing — receipts round to whole đồng). All timestamps are
tz-aware in VN_TZ.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class CDRKind(str, Enum):
    """Three billable CDR kinds covering ~95% of telecom volume."""

    VOICE = "VOICE"
    SMS = "SMS"
    DATA = "DATA"


class Carrier(str, Enum):
    """Five VN mobile carriers (2026 market share approx)."""

    VIETTEL = "VIETTEL"  # Viettel Mobile (53% market share)
    VINAPHONE = "VINAPHONE"  # VNPT-VinaPhone (24%)
    MOBIFONE = "MOBIFONE"  # MobiFone (17%)
    VIETNAMOBILE = "VIETNAMOBILE"  # ~3%
    REDDI = "REDDI"  # Mobicast/Reddi (~1%)
    UNKNOWN = "UNKNOWN"  # foreign / unallocated prefix


class PlanKind(str, Enum):
    """Two contractual flavours."""

    PREPAID = "PREPAID"  # Trả trước — top-up balance
    POSTPAID = "POSTPAID"  # Trả sau — monthly statement


@dataclass(frozen=True, slots=True)
class CDR:
    """One Call Detail Record.

    ``subscriber_msisdn`` is the subscribing E.164-formatted phone
    number (e.g. ``"+84961234567"``); ``peer_msisdn`` is the other
    party (callee for VOICE/SMS, ``""`` for DATA).
    """

    cdr_id: str
    subscriber_msisdn: str
    peer_msisdn: str
    kind: CDRKind
    occurred_at: datetime
    duration_seconds: int = 0  # only VOICE
    bytes_used: int = 0  # only DATA
    n_messages: int = 0  # only SMS
    is_roaming: bool = False  # subscriber is outside VN
    is_premium: bool = False  # peer is on a premium-rate prefix

    def __post_init__(self) -> None:
        if not self.cdr_id:
            raise ValueError("cdr_id must be non-empty")
        if not self.subscriber_msisdn:
            raise ValueError("subscriber_msisdn must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")
        if self.bytes_used < 0:
            raise ValueError("bytes_used must be >= 0")
        if self.n_messages < 0:
            raise ValueError("n_messages must be >= 0")
        # Kind-specific invariants.
        if self.kind is CDRKind.VOICE:
            if self.duration_seconds == 0:
                raise ValueError("VOICE CDRs must have duration_seconds > 0")
            if self.bytes_used > 0 or self.n_messages > 0:
                raise ValueError("VOICE CDRs cannot have bytes_used / n_messages")
        elif self.kind is CDRKind.SMS:
            if self.n_messages == 0:
                raise ValueError("SMS CDRs must have n_messages > 0")
            if self.duration_seconds > 0 or self.bytes_used > 0:
                raise ValueError("SMS CDRs cannot have duration_seconds / bytes_used")
        elif self.kind is CDRKind.DATA:
            if self.bytes_used == 0:
                raise ValueError("DATA CDRs must have bytes_used > 0")
            if self.duration_seconds > 0 or self.n_messages > 0:
                raise ValueError("DATA CDRs cannot have duration_seconds / n_messages")


@dataclass(frozen=True, slots=True)
class RatedCDR:
    """A CDR after pricing — carries the rated amount in integer VND."""

    cdr: CDR
    subscriber_carrier: Carrier
    peer_carrier: Carrier
    rated_amount_vnd: int  # pre-VAT
    vat_amount_vnd: int  # 10% of rated_amount (per VN VAT Law)
    is_peak: bool  # voice was during peak hours

    def __post_init__(self) -> None:
        if self.rated_amount_vnd < 0:
            raise ValueError("rated_amount_vnd must be >= 0")
        if self.vat_amount_vnd < 0:
            raise ValueError("vat_amount_vnd must be >= 0")

    @property
    def total_vnd(self) -> int:
        """Total billed (rated + VAT)."""
        return self.rated_amount_vnd + self.vat_amount_vnd


@dataclass(frozen=True, slots=True)
class MonthlyBill:
    """Aggregated monthly bill for one subscriber."""

    subscriber_msisdn: str
    carrier: Carrier
    plan_kind: PlanKind
    billing_month: str  # ISO year-month "2026-05"
    n_voice_cdrs: int
    n_sms_cdrs: int
    n_data_cdrs: int
    total_voice_seconds: int
    total_sms: int
    total_bytes: int
    pre_vat_amount_vnd: int
    vat_amount_vnd: int

    def __post_init__(self) -> None:
        if self.pre_vat_amount_vnd < 0:
            raise ValueError("pre_vat_amount_vnd must be >= 0")
        if self.vat_amount_vnd < 0:
            raise ValueError("vat_amount_vnd must be >= 0")

    @property
    def total_amount_vnd(self) -> int:
        return self.pre_vat_amount_vnd + self.vat_amount_vnd

    @property
    def total_cdrs(self) -> int:
        return self.n_voice_cdrs + self.n_sms_cdrs + self.n_data_cdrs


__all__ = [
    "VN_TZ",
    "CDR",
    "CDRKind",
    "Carrier",
    "MonthlyBill",
    "PlanKind",
    "RatedCDR",
]
