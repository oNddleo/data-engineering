"""Alert types and severities emitted by rules.

Severity is what the on-call rotation cares about — INFO is for
warehouse-only enrichment, WARN goes to the daily fraud-review
queue, CRIT pages the duty officer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Alert severity tier."""

    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


class AlertKind(str, Enum):
    """The five alert kinds the bundled rules can emit."""

    BIO_REQUIRED_SINGLE_TXN = "BIO_REQUIRED_SINGLE_TXN"
    """Decision 2345: single transfer > 10M VND without biometric auth."""

    BIO_REQUIRED_CUMULATIVE = "BIO_REQUIRED_CUMULATIVE"
    """Decision 2345: this transfer would push daily cumulative > 20M VND without biometric."""

    VELOCITY_SPIKE = "VELOCITY_SPIKE"
    """An account is initiating more transfers per minute than its baseline."""

    STRUCTURING_SUSPECTED = "STRUCTURING_SUSPECTED"
    """Multiple just-below-10M transfers within a short window — classic
    smurfing pattern to dodge the single-txn biometric trigger."""

    BLACKLIST_HIT = "BLACKLIST_HIT"
    """Beneficiary account is on the blacklist (e.g. known mule, frozen
    by criminal investigation, sanctioned)."""


@dataclass(frozen=True, slots=True)
class Alert:
    """A single anomaly fired by a rule for one transaction."""

    kind: AlertKind
    severity: Severity
    txn_id: str
    account: str
    detail: str
    amount_vnd: int


__all__ = ["Alert", "AlertKind", "Severity"]
