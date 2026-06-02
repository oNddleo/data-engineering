"""Borrower + credit-history data model.

What a CIC report looks like in our shape:

* **Borrower** — identified by CCCD/CMND (we use an opaque
  ``borrower_id``). Has a list of credit contracts, a list of monthly
  group assessments per contract, and a list of inquiry events
  (other banks pulling CIC for them).
* **CreditContract** — one loan or card from one bank. Has an
  opening date, optional closing date (None == active), product
  type, and the original credit amount.
* **GroupAssessment** — the CIC group + outstanding amounts for one
  contract on the first of one calendar month. CIC reports are
  monthly snapshots; we follow the same cadence.
* **Inquiry** — a bank pulling the borrower's CIC report. Banks
  watch each other's inquiries to detect "credit shopping".

All money is integer VND. All months are represented as the first
day of that month (``date(year, month, 1)``).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cicscore.cic_groups import CICGroup


class ContractType(str, Enum):
    """Product types we distinguish for credit scoring purposes."""

    TERM_LOAN = "TERM_LOAN"  # vay tiêu dùng kỳ hạn
    MORTGAGE = "MORTGAGE"  # vay mua nhà / thế chấp BĐS
    AUTO_LOAN = "AUTO_LOAN"  # vay mua xe
    CREDIT_CARD = "CREDIT_CARD"  # thẻ tín dụng
    OVERDRAFT = "OVERDRAFT"  # thấu chi tài khoản
    BUSINESS_LOAN = "BUSINESS_LOAN"


@dataclass(frozen=True, slots=True)
class CreditContract:
    """One credit contract — a loan or card from one lender."""

    contract_id: str
    borrower_id: str
    lender_bank: str
    contract_type: ContractType
    original_amount_vnd: int
    opened_at: date
    closed_at: date | None = None

    def __post_init__(self) -> None:
        if not self.contract_id:
            raise ValueError("contract_id must be non-empty")
        if not self.borrower_id:
            raise ValueError("borrower_id must be non-empty")
        if not self.lender_bank:
            raise ValueError("lender_bank must be non-empty")
        if self.original_amount_vnd <= 0:
            raise ValueError(f"original_amount_vnd must be > 0, got {self.original_amount_vnd}")
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("closed_at cannot be before opened_at")

    def is_active_on(self, d: date) -> bool:
        """True iff the contract was open at any point on or before ``d`` and not yet closed by ``d``."""
        if self.opened_at > d:
            return False
        return self.closed_at is None or self.closed_at > d


@dataclass(frozen=True, slots=True)
class GroupAssessment:
    """One contract's CIC group + outstanding state as of a calendar month."""

    contract_id: str
    as_of_month: date
    group: CICGroup
    outstanding_principal_vnd: int
    outstanding_interest_vnd: int = 0
    days_past_due: int = 0

    def __post_init__(self) -> None:
        if self.as_of_month.day != 1:
            raise ValueError(
                f"as_of_month must be the first of a month, got {self.as_of_month.isoformat()}"
            )
        if self.outstanding_principal_vnd < 0:
            raise ValueError(
                f"outstanding_principal_vnd must be >= 0, got {self.outstanding_principal_vnd}"
            )
        if self.outstanding_interest_vnd < 0:
            raise ValueError(
                f"outstanding_interest_vnd must be >= 0, got {self.outstanding_interest_vnd}"
            )
        if self.days_past_due < 0:
            raise ValueError(f"days_past_due must be >= 0, got {self.days_past_due}")


@dataclass(frozen=True, slots=True)
class Inquiry:
    """One CIC-pull event — a bank looking up this borrower."""

    borrower_id: str
    lender_bank: str
    inquired_at: date
    purpose: str = "NEW_LOAN"

    def __post_init__(self) -> None:
        if not self.borrower_id:
            raise ValueError("borrower_id must be non-empty")
        if not self.lender_bank:
            raise ValueError("lender_bank must be non-empty")


@dataclass(frozen=True, slots=True)
class Borrower:
    """All credit info we have about one borrower (CCCD/CMND)."""

    borrower_id: str
    contracts: tuple[CreditContract, ...] = field(default_factory=tuple)
    assessments: tuple[GroupAssessment, ...] = field(default_factory=tuple)
    inquiries: tuple[Inquiry, ...] = field(default_factory=tuple)
    monthly_income_vnd: int | None = None

    def __post_init__(self) -> None:
        if not self.borrower_id:
            raise ValueError("borrower_id must be non-empty")
        for c in self.contracts:
            if c.borrower_id != self.borrower_id:
                raise ValueError(
                    f"contract {c.contract_id} has borrower_id={c.borrower_id} "
                    f"but parent borrower_id={self.borrower_id}"
                )
        contract_ids = {c.contract_id for c in self.contracts}
        for a in self.assessments:
            if a.contract_id not in contract_ids:
                raise ValueError(f"assessment references unknown contract_id={a.contract_id}")
        for q in self.inquiries:
            if q.borrower_id != self.borrower_id:
                raise ValueError(
                    f"inquiry has borrower_id={q.borrower_id} but parent borrower_id={self.borrower_id}"
                )
        if self.monthly_income_vnd is not None and self.monthly_income_vnd < 0:
            raise ValueError(
                f"monthly_income_vnd must be >= 0 or None, got {self.monthly_income_vnd}"
            )


# ---------------------------------------------------------------------------
# Month / date helpers — used widely across feature extraction.


def first_of_month(d: date) -> date:
    """Return the first-of-month for ``d``."""
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    """Add ``n`` months to ``d``; clamp day to month length."""
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def months_between(later: date, earlier: date) -> int:
    """Whole-month difference (signed) between two dates."""
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


__all__ = [
    "Borrower",
    "ContractType",
    "CreditContract",
    "GroupAssessment",
    "Inquiry",
    "add_months",
    "first_of_month",
    "months_between",
]
