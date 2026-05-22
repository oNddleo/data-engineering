"""Data classes for the reconciliation domain."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date  # noqa: TCH003


class DiscrepancyType(str, enum.Enum):
    MATCHED = "matched"
    AMOUNT_MISMATCH = "amount_mismatch"
    TIMING = "timing"
    ROUNDING = "rounding"
    MISSING = "missing"
    MULTI = "multi"


@dataclass(frozen=True)
class Transaction:
    source: str
    ref: str
    amount: float
    txn_date: date
    description: str
    currency: str = "USD"


@dataclass
class MatchResult:
    ref: str
    status: DiscrepancyType
    sources_present: list[str]
    transactions: list[Transaction]
    amount_delta: float = 0.0
    confidence: float = 1.0
    notes: str = ""


@dataclass
class ReconReport:
    run_date: date
    sources: list[str]
    total_records: int
    matched: int
    discrepancies: int
    results: list[MatchResult] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.matched / len(self.results)
