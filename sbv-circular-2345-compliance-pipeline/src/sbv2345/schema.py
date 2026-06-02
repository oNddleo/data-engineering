"""Schema for the SBV 2345 audit-trail pipeline.

The data flow is:

```
TransactionEvent  --(classify)-->  AuditEvent  --(seal)-->  SealedAuditRecord
   (raw input)       triggers + bases         hash-chained + sequence-numbered
```

* :class:`TransactionEvent` — what arrives from upstream (Kafka /
  core-banking export / NAPAS feed). Every customer-initiated
  transfer flows past us, regardless of value or auth method.
* :class:`AuditEvent` — a TransactionEvent annotated with which
  Decision-2345 trigger(s) apply and the legal-basis text for
  each. If no triggers fire, the event is *not* an audit event —
  the ledger only stores audit-worthy rows.
* :class:`SealedAuditRecord` — what the ledger actually persists:
  the AuditEvent plus its sequence number, the chain hash of the
  previous record, this record's hash, and the wall-clock seal
  time.

VND is always integer. Timestamps are always tz-aware UTC+7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
"""Vietnam Standard Time. No DST."""


class Channel(str, Enum):
    """Initiation channel of the transfer."""

    MOBILE_APP = "MOBILE_APP"
    INTERNET_BANKING = "INTERNET_BANKING"
    ATM = "ATM"
    BRANCH = "BRANCH"


class AuthMethod(str, Enum):
    """The strongest auth factor the customer cleared on this txn."""

    PIN = "PIN"
    OTP = "OTP"
    BIOMETRIC = "BIOMETRIC"
    NONE = "NONE"  # declined / authentication failed


class BiometricMethod(str, Enum):
    """The biometric modality, when ``auth_method == BIOMETRIC``."""

    FACE = "FACE"
    FINGERPRINT = "FINGERPRINT"
    VOICE = "VOICE"
    IRIS = "IRIS"


class TriggerKind(str, Enum):
    """Why a transaction is subject to Decision 2345 audit logging."""

    SINGLE_TXN_OVER_10M = "SINGLE_TXN_OVER_10M"
    """Single transfer value > 10,000,000 VND — Điều 1.1."""

    DAILY_CUMULATIVE_OVER_20M = "DAILY_CUMULATIVE_OVER_20M"
    """Daily cumulative > 20,000,000 VND from the same account — Điều 1.2."""

    HIGH_RISK_BENEFICIARY = "HIGH_RISK_BENEFICIARY"
    """Beneficiary account is on a sanctioned / mule / frozen list."""

    INTERNATIONAL_TRANSFER = "INTERNATIONAL_TRANSFER"
    """Cross-border transfer — captured for SBV foreign-exchange reports."""


@dataclass(frozen=True, slots=True)
class TransactionEvent:
    """A raw transaction received by the audit pipeline."""

    txn_id: str
    initiator_account: str
    beneficiary_account: str
    amount_vnd: int
    channel: Channel
    occurred_at: datetime
    auth_method: AuthMethod
    biometric_method: BiometricMethod | None = None
    cross_border: bool = False
    initiator_bank_bin: str = ""
    beneficiary_bank_bin: str = ""

    def __post_init__(self) -> None:
        if not self.txn_id:
            raise ValueError("txn_id must be non-empty")
        if not self.initiator_account or not self.beneficiary_account:
            raise ValueError("account fields must be non-empty")
        if self.amount_vnd <= 0:
            raise ValueError(f"amount_vnd must be > 0, got {self.amount_vnd}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.auth_method is AuthMethod.BIOMETRIC and self.biometric_method is None:
            raise ValueError("biometric_method required when auth_method is BIOMETRIC")
        if self.auth_method is not AuthMethod.BIOMETRIC and self.biometric_method is not None:
            raise ValueError("biometric_method set but auth_method is not BIOMETRIC — inconsistent")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A classified transaction — the input to the sealing step."""

    txn: TransactionEvent
    triggered_kinds: tuple[TriggerKind, ...]
    legal_bases: tuple[str, ...] = field(default_factory=tuple)
    daily_cumulative_after_vnd: int = 0
    """Per-account daily total *including* this transaction. Helps auditors
    explain why DAILY_CUMULATIVE_OVER_20M fired without recomputing."""

    def __post_init__(self) -> None:
        if not self.triggered_kinds:
            raise ValueError("AuditEvent requires >= 1 triggered_kind")
        if len(self.triggered_kinds) != len(set(self.triggered_kinds)):
            raise ValueError("triggered_kinds must be deduplicated")
        if self.legal_bases and len(self.legal_bases) != len(self.triggered_kinds):
            raise ValueError("legal_bases, when supplied, must be parallel to triggered_kinds")


__all__ = [
    "VN_TZ",
    "AuditEvent",
    "AuthMethod",
    "BiometricMethod",
    "Channel",
    "TransactionEvent",
    "TriggerKind",
]
