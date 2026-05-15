"""Schema for the real-time fraud-detection pipeline.

Three data shapes flow through the engine:

* :class:`TransactionRequest` — what the banking app sends when a
  user clicks "Confirm" on a transfer screen. We need to return a
  decision before the transfer is executed.
* :class:`SignalHit` — one rule firing. Carries a name (e.g.
  ``KEYWORD_CONG_AN``), a point weight, and a human-readable
  detail.
* :class:`FraudDecision` — the engine's verdict: an aggregate score,
  the signal trail that produced it, and the measured evaluation
  latency. The decision tier (ALLOW/REVIEW/BLOCK) is derived from
  the score.

All datetimes are tz-aware UTC+7. All money is integer VND.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Channel(str, Enum):
    """The channel through which the user initiated the transfer."""

    MOBILE_APP = "MOBILE_APP"
    INTERNET_BANKING = "INTERNET_BANKING"
    ATM = "ATM"
    BRANCH = "BRANCH"


class Decision(str, Enum):
    """The engine's verdict on a pending transaction."""

    ALLOW = "ALLOW"
    """Score below review threshold — proceed normally."""

    REVIEW = "REVIEW"
    """Score in the warn band — hold for human review."""

    BLOCK = "BLOCK"
    """Score in the critical band — reject the transfer."""


@dataclass(frozen=True, slots=True)
class TransactionRequest:
    """A pending transfer awaiting fraud-engine decision."""

    txn_id: str
    initiator_account: str
    beneficiary_account: str
    beneficiary_bank_bin: str
    amount_vnd: int
    narrative: str
    channel: Channel
    occurred_at: datetime
    otp_issued_at: datetime | None = None
    otp_verified_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.txn_id:
            raise ValueError("txn_id must be non-empty")
        if not self.initiator_account or not self.beneficiary_account:
            raise ValueError("account fields must be non-empty")
        if self.amount_vnd <= 0:
            raise ValueError(f"amount_vnd must be > 0, got {self.amount_vnd}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if (self.otp_issued_at is None) != (self.otp_verified_at is None):
            raise ValueError("otp_issued_at and otp_verified_at must both be set or both None")
        if self.otp_issued_at is not None and self.otp_verified_at is not None:
            if self.otp_issued_at.tzinfo is None or self.otp_verified_at.tzinfo is None:
                raise ValueError("OTP timestamps must be timezone-aware")
            if self.otp_verified_at < self.otp_issued_at:
                raise ValueError("otp_verified_at cannot precede otp_issued_at")


@dataclass(frozen=True, slots=True)
class SignalHit:
    """One rule's contribution to the fraud score."""

    name: str
    points: int
    detail: str


@dataclass(frozen=True, slots=True)
class FraudDecision:
    """The engine's output for one transaction."""

    txn_id: str
    decision: Decision
    score: int
    signals: tuple[SignalHit, ...] = field(default_factory=tuple)
    latency_ms: float = 0.0

    def has_signal(self, name: str) -> bool:
        return any(s.name == name for s in self.signals)


__all__ = [
    "VN_TZ",
    "Channel",
    "Decision",
    "FraudDecision",
    "SignalHit",
    "TransactionRequest",
]
