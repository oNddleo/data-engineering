"""Alert types emitted by AML pattern detectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AlertKind(str, Enum):
    """The five classic AML patterns this detector flags."""

    FAN_OUT = "FAN_OUT"
    """One source spraying money to many distinct destinations."""

    FAN_IN = "FAN_IN"
    """One destination receiving from many distinct sources."""

    LAYERING_CHAIN = "LAYERING_CHAIN"
    """A sequence A → B → C → ... of N+ hops within a short window."""

    ROUND_TRIP = "ROUND_TRIP"
    """Money returns to the originating account after passing through ≥ 1 intermediary."""

    STRUCTURED_DEPOSIT = "STRUCTURED_DEPOSIT"
    """Multiple just-below-threshold incoming transfers to the same account."""


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


@dataclass(frozen=True, slots=True)
class AMLAlert:
    """One AML-pattern hit, scoped to a primary account."""

    kind: AlertKind
    severity: Severity
    primary_account: str
    related_accounts: tuple[str, ...] = field(default_factory=tuple)
    total_amount_vnd: int = 0
    detail: str = ""
    txn_ids: tuple[str, ...] = field(default_factory=tuple)


__all__ = ["AMLAlert", "AlertKind", "Severity"]
