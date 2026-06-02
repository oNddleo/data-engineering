"""Node + edge schema for the transaction graph.

Nodes are :class:`Account` objects; edges are :class:`Transaction`
records carrying the direction (``from_account → to_account``), the
amount, and the wall-clock timestamp. We use a directed multigraph
because two accounts can transact many times in either direction
within a window.

Risk flags on an account are caller-supplied — typically the result
of a separate KYC / sanctions-screening process upstream of this
detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
"""Vietnam Standard Time."""


class AccountType(str, Enum):
    """How we classify the account holder."""

    PERSONAL = "PERSONAL"
    BUSINESS = "BUSINESS"
    GOVERNMENT = "GOVERNMENT"
    SHELL = "SHELL"  # nominee / shell-company suspected
    UNKNOWN = "UNKNOWN"


class Channel(str, Enum):
    MOBILE_APP = "MOBILE_APP"
    INTERNET_BANKING = "INTERNET_BANKING"
    ATM = "ATM"
    BRANCH = "BRANCH"
    CARD = "CARD"


class RiskFlag(str, Enum):
    """Flags that boost an account's a-priori risk score."""

    PEP = "PEP"  # Politically Exposed Person
    SANCTIONED = "SANCTIONED"
    MULE_SUSPECTED = "MULE_SUSPECTED"
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"
    PRIOR_SAR = "PRIOR_SAR"  # had a Suspicious Activity Report filed before


@dataclass(frozen=True, slots=True)
class Account:
    """A node in the transaction graph."""

    account_id: str
    bank_bin: str
    account_type: AccountType = AccountType.PERSONAL
    risk_flags: tuple[RiskFlag, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id must be non-empty")
        if len(self.bank_bin) != 6 or not self.bank_bin.isdigit():
            raise ValueError(f"bank_bin must be 6 digits, got {self.bank_bin!r}")
        if len(set(self.risk_flags)) != len(self.risk_flags):
            raise ValueError("risk_flags must be deduplicated")


@dataclass(frozen=True, slots=True)
class Transaction:
    """A directed weighted edge — one transfer from ``from_account`` to ``to_account``."""

    txn_id: str
    from_account: str
    to_account: str
    amount_vnd: int
    occurred_at: datetime
    channel: Channel = Channel.MOBILE_APP

    def __post_init__(self) -> None:
        if not self.txn_id:
            raise ValueError("txn_id must be non-empty")
        if not self.from_account or not self.to_account:
            raise ValueError("from_account and to_account must be non-empty")
        if self.from_account == self.to_account:
            raise ValueError("self-transactions are not allowed (no self-loops)")
        if self.amount_vnd <= 0:
            raise ValueError(f"amount_vnd must be > 0, got {self.amount_vnd}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


__all__ = [
    "VN_TZ",
    "Account",
    "AccountType",
    "Channel",
    "RiskFlag",
    "Transaction",
]
