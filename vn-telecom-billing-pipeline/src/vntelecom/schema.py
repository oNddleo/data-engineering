"""Core domain types for VN telecom CDR billing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Operator(str, Enum):
    """Vietnam mobile network operators."""

    VIETTEL = "VIETTEL"
    MOBIFONE = "MOBIFONE"
    VINAPHONE = "VINAPHONE"
    VIETNAMOBILE = "VIETNAMOBILE"
    GMOBILE = "GMOBILE"


class CallType(str, Enum):
    """Voice call routing type."""

    ON_NET = "ON_NET"  # same operator
    OFF_NET = "OFF_NET"  # different domestic operator
    ROAMING_IN = "ROAMING_IN"  # foreign subscriber on VN network
    ROAMING_OUT = "ROAMING_OUT"  # VN subscriber abroad
    INTERNATIONAL = "INTERNATIONAL"
    LANDLINE = "LANDLINE"


class ServiceType(str, Enum):
    """Telecom service type."""

    VOICE = "VOICE"
    SMS = "SMS"
    MMS = "MMS"
    DATA = "DATA"  # mobile data (MB)
    PREMIUM = "PREMIUM"  # premium SMS/content


@dataclass(frozen=True, slots=True)
class CDR:
    """Call Detail Record (raw, before billing)."""

    cdr_id: str
    subscriber_msisdn: str  # e.g. "0901234567"
    operator: Operator
    service_type: ServiceType
    call_type: CallType  # only meaningful for VOICE
    duration_seconds: int  # voice: actual seconds; SMS: 1; DATA: volume in KB
    timestamp_epoch_s: int
    destination_msisdn: str  # "" for data
    is_prepaid: bool

    def __post_init__(self) -> None:
        if not self.cdr_id:
            raise ValueError("cdr_id cannot be empty")
        if not self.subscriber_msisdn:
            raise ValueError("subscriber_msisdn cannot be empty")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")
        if self.timestamp_epoch_s <= 0:
            raise ValueError("timestamp_epoch_s must be positive")
