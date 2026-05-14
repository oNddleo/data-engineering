"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import date

from cicscore.cic_groups import CICGroup
from cicscore.schema import (
    Borrower,
    ContractType,
    CreditContract,
    GroupAssessment,
    Inquiry,
)


def make_contract(
    *,
    contract_id: str = "C-1",
    borrower_id: str = "B-1",
    lender_bank: str = "VCB",
    contract_type: ContractType = ContractType.TERM_LOAN,
    original_amount: int = 100_000_000,
    opened_at: date | None = None,
    closed_at: date | None = None,
) -> CreditContract:
    return CreditContract(
        contract_id=contract_id,
        borrower_id=borrower_id,
        lender_bank=lender_bank,
        contract_type=contract_type,
        original_amount_vnd=original_amount,
        opened_at=opened_at or date(2024, 1, 1),
        closed_at=closed_at,
    )


def make_assessment(
    *,
    contract_id: str = "C-1",
    as_of_month: date,
    group: CICGroup = CICGroup.GROUP_1,
    principal: int = 50_000_000,
    interest: int = 600_000,
    days_past_due: int = 0,
) -> GroupAssessment:
    return GroupAssessment(
        contract_id=contract_id,
        as_of_month=as_of_month,
        group=group,
        outstanding_principal_vnd=principal,
        outstanding_interest_vnd=interest,
        days_past_due=days_past_due,
    )


def make_inquiry(
    *,
    borrower_id: str = "B-1",
    lender_bank: str = "MB",
    inquired_at: date,
    purpose: str = "NEW_LOAN",
) -> Inquiry:
    return Inquiry(
        borrower_id=borrower_id,
        lender_bank=lender_bank,
        inquired_at=inquired_at,
        purpose=purpose,
    )


def make_borrower(
    *,
    borrower_id: str = "B-1",
    contracts: tuple[CreditContract, ...] = (),
    assessments: tuple[GroupAssessment, ...] = (),
    inquiries: tuple[Inquiry, ...] = (),
    monthly_income_vnd: int | None = None,
) -> Borrower:
    return Borrower(
        borrower_id=borrower_id,
        contracts=contracts,
        assessments=assessments,
        inquiries=inquiries,
        monthly_income_vnd=monthly_income_vnd,
    )


__all__ = [
    "make_assessment",
    "make_borrower",
    "make_contract",
    "make_inquiry",
]
