"""NAPAS 247 transaction record + supporting enums.

NAPAS 247 is the State Bank of Vietnam's 24/7 instant inter-bank
transfer rail — every retail VND transfer that completes in seconds
goes through it. The shape below is what a monitor sees on the
ingress side, not the full ISO 20022 message: we strip everything
not relevant to anomaly detection.

Decision 2345/QĐ-NHNN (in force 2024-07-01) is the regulation that
makes the ``biometric_verified`` flag load-bearing: any transfer over
10 million VND requires a biometric capture, and once an account's
daily cumulative crosses 20 million VND every subsequent transfer
that day requires one too.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
"""Vietnam Standard Time (Indochina Time). No DST."""


class Channel(str, Enum):
    """How the transfer was initiated."""

    MOBILE_APP = "MOBILE_APP"
    INTERNET_BANKING = "INTERNET_BANKING"
    ATM = "ATM"
    BRANCH = "BRANCH"


@dataclass(frozen=True, slots=True)
class Transaction:
    """One NAPAS 247 transfer event observed on the monitor's input."""

    txn_id: str
    initiator_account: str
    initiator_bank_bin: str
    beneficiary_account: str
    beneficiary_bank_bin: str
    amount_vnd: int
    channel: Channel
    occurred_at: datetime
    biometric_verified: bool
    device_id: str | None = None
    geo_ip: str | None = None

    def __post_init__(self) -> None:
        if self.amount_vnd <= 0:
            raise ValueError(f"amount_vnd must be > 0, got {self.amount_vnd}")
        if not self.txn_id:
            raise ValueError("txn_id must be non-empty")
        if not self.initiator_account or not self.beneficiary_account:
            raise ValueError("account fields must be non-empty")
        if len(self.initiator_bank_bin) != 6 or not self.initiator_bank_bin.isdigit():
            raise ValueError(
                f"initiator_bank_bin must be 6 digits, got {self.initiator_bank_bin!r}"
            )
        if len(self.beneficiary_bank_bin) != 6 or not self.beneficiary_bank_bin.isdigit():
            raise ValueError(
                f"beneficiary_bank_bin must be 6 digits, got {self.beneficiary_bank_bin!r}"
            )
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


__all__ = ["VN_TZ", "Channel", "Transaction"]
