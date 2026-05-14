"""Point-in-time feature engineering from a borrower's CIC history.

Every feature is computed **as of an explicit observation_date**.
Any data dated *after* that observation date is filtered out
before the feature is computed — no look-ahead bias.

Conventions:

* ``observation_date`` is a regular calendar date. The most recent
  CIC assessment month we consider is
  ``first_of_month(observation_date)``.
* Active-contract filtering is strict: ``opened_at <= observation_date``
  and (``closed_at is None`` OR ``closed_at > observation_date``).
* "24-month" features use the 24 monthly snapshot windows ending at
  ``first_of_month(observation_date)``. So at obs_date 2026-05-14
  the window is 2024-06-01 … 2026-05-01.
* Group-2-plus is the canonical Vietnamese-banking shorthand for
  "borrower currently has a problem"; we expose its
  prevalence both as a max group and as a count of distinct months
  any contract was at group ≥ 2.

Effective-borrower-group (Thông tư 11/2021 Điều 11) — the rule that
*all* of a borrower's contracts get reclassified to the worst single
contract's group — is applied here. So the "current_max_group"
feature reflects the regulatory borrower-level classification, not
a single contract's status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cicscore.cic_groups import PROVISION_RATE, CICGroup
from cicscore.schema import ContractType, add_months, first_of_month, months_between

if TYPE_CHECKING:
    from datetime import date

    from cicscore.schema import Borrower, CreditContract, GroupAssessment, Inquiry


@dataclass(frozen=True, slots=True)
class FeatureVector:
    """All features computed at one observation date for one borrower."""

    borrower_id: str
    observation_date: date

    # CIC group features.
    current_max_group: CICGroup | None
    worst_group_ever: CICGroup | None
    max_group_24m: CICGroup | None
    months_in_group_2plus_24m: int

    # Exposure.
    active_contracts: int
    unique_lenders: int
    total_outstanding_principal_vnd: int
    total_outstanding_interest_vnd: int
    provision_estimate_vnd: int

    # Tenure.
    months_since_first_credit: int | None
    months_since_last_credit_open: int | None

    # Inquiries.
    inquiries_3m: int
    inquiries_6m: int
    inquiries_12m: int
    days_since_last_inquiry: int | None

    # Product mix.
    has_term_loan: bool
    has_mortgage: bool
    has_auto_loan: bool
    has_credit_card: bool
    has_overdraft: bool
    has_business_loan: bool

    # Debt-to-income (None if income unknown).
    dti_ratio: float | None


# ---------------------------------------------------------------------------
# Filtering helpers


def _active_contracts(borrower: Borrower, obs_date: date) -> list[CreditContract]:
    return [c for c in borrower.contracts if c.is_active_on(obs_date)]


def _opened_contracts(borrower: Borrower, obs_date: date) -> list[CreditContract]:
    """All contracts opened on or before ``obs_date`` (regardless of close state)."""
    return [c for c in borrower.contracts if c.opened_at <= obs_date]


def _visible_assessments(
    borrower: Borrower,
    obs_date: date,
    *,
    since_month: date | None = None,
) -> list[GroupAssessment]:
    """Assessments whose ``as_of_month`` lies in (since_month, first_of_month(obs_date)]."""
    cutoff_max = first_of_month(obs_date)
    out = [a for a in borrower.assessments if a.as_of_month <= cutoff_max]
    if since_month is not None:
        out = [a for a in out if a.as_of_month >= since_month]
    return out


def _visible_inquiries(borrower: Borrower, obs_date: date) -> list[Inquiry]:
    return [q for q in borrower.inquiries if q.inquired_at <= obs_date]


def _latest_per_contract(
    assessments: list[GroupAssessment],
) -> dict[str, GroupAssessment]:
    """Per contract_id, return the assessment with the most recent ``as_of_month``."""
    latest: dict[str, GroupAssessment] = {}
    for a in assessments:
        cur = latest.get(a.contract_id)
        if cur is None or a.as_of_month > cur.as_of_month:
            latest[a.contract_id] = a
    return latest


# ---------------------------------------------------------------------------
# Monthly-payment estimator — used for DTI.

_MONTHLY_PAYMENT_FACTOR: dict[ContractType, float] = {
    # Roughly 36-month amortisation for vanilla term loans.
    ContractType.TERM_LOAN: 1 / 36,
    ContractType.AUTO_LOAN: 1 / 36,
    ContractType.BUSINESS_LOAN: 1 / 36,
    # Mortgages amortise over 20 years.
    ContractType.MORTGAGE: 1 / 240,
    # Credit cards: 5 % minimum payment per month is the VN regulator floor.
    ContractType.CREDIT_CARD: 0.05,
    # Overdrafts: interest-only ~2 %/month on outstanding.
    ContractType.OVERDRAFT: 0.02,
}


def _estimate_monthly_payment_vnd(contract: CreditContract, outstanding_principal_vnd: int) -> int:
    factor = _MONTHLY_PAYMENT_FACTOR[contract.contract_type]
    return int(outstanding_principal_vnd * factor)


# ---------------------------------------------------------------------------
# Public API


def extract(borrower: Borrower, observation_date: date) -> FeatureVector:
    """Compute one feature row for one borrower at one observation date."""
    obs_month = first_of_month(observation_date)
    window_24m_start = add_months(obs_month, -23)  # 24 months inclusive: [obs-23, obs]

    actives = _active_contracts(borrower, observation_date)
    opened = _opened_contracts(borrower, observation_date)
    visible = _visible_assessments(borrower, observation_date)
    visible_24m = _visible_assessments(borrower, observation_date, since_month=window_24m_start)
    inquiries = _visible_inquiries(borrower, observation_date)

    # --- Group features ----------------------------------------------------
    worst_group_ever = max((a.group for a in visible), default=None)
    max_group_24m = max((a.group for a in visible_24m), default=None)
    # Effective borrower-level group at observation: max across latest per active contract.
    active_ids = {c.contract_id for c in actives}
    latest_per_active = _latest_per_contract([a for a in visible if a.contract_id in active_ids])
    current_max_group = max((a.group for a in latest_per_active.values()), default=None)

    # months_in_group_2plus_24m — distinct months where ANY contract was group ≥ 2.
    months_with_problem: set[date] = set()
    for a in visible_24m:
        if a.group >= CICGroup.GROUP_2:
            months_with_problem.add(a.as_of_month)
    months_in_group_2plus_24m = len(months_with_problem)

    # --- Exposure ----------------------------------------------------------
    total_principal = 0
    total_interest = 0
    provision_total = 0
    for c in actives:
        latest = latest_per_active.get(c.contract_id)
        if latest is None:
            continue
        total_principal += latest.outstanding_principal_vnd
        total_interest += latest.outstanding_interest_vnd
        provision_total += int(latest.outstanding_principal_vnd * PROVISION_RATE[latest.group])
    unique_lenders = len({c.lender_bank for c in actives})

    # --- Tenure ------------------------------------------------------------
    first_open = min((c.opened_at for c in opened), default=None)
    last_open = max((c.opened_at for c in opened), default=None)
    months_since_first_credit = (
        months_between(observation_date, first_open) if first_open is not None else None
    )
    months_since_last_credit_open = (
        months_between(observation_date, last_open) if last_open is not None else None
    )

    # --- Inquiries ---------------------------------------------------------
    def _window_count(months: int) -> int:
        start = add_months(observation_date, -months)
        return sum(1 for q in inquiries if q.inquired_at >= start)

    inquiries_3m = _window_count(3)
    inquiries_6m = _window_count(6)
    inquiries_12m = _window_count(12)
    last_inquiry = max((q.inquired_at for q in inquiries), default=None)
    days_since_last_inquiry = (
        (observation_date - last_inquiry).days if last_inquiry is not None else None
    )

    # --- Product mix -------------------------------------------------------
    active_types = {c.contract_type for c in actives}

    # --- DTI ---------------------------------------------------------------
    dti_ratio: float | None = None
    if borrower.monthly_income_vnd is not None and borrower.monthly_income_vnd > 0:
        monthly_payment = 0
        for c in actives:
            latest = latest_per_active.get(c.contract_id)
            if latest is None:
                continue
            monthly_payment += _estimate_monthly_payment_vnd(c, latest.outstanding_principal_vnd)
        dti_ratio = monthly_payment / borrower.monthly_income_vnd

    return FeatureVector(
        borrower_id=borrower.borrower_id,
        observation_date=observation_date,
        current_max_group=current_max_group,
        worst_group_ever=worst_group_ever,
        max_group_24m=max_group_24m,
        months_in_group_2plus_24m=months_in_group_2plus_24m,
        active_contracts=len(actives),
        unique_lenders=unique_lenders,
        total_outstanding_principal_vnd=total_principal,
        total_outstanding_interest_vnd=total_interest,
        provision_estimate_vnd=provision_total,
        months_since_first_credit=months_since_first_credit,
        months_since_last_credit_open=months_since_last_credit_open,
        inquiries_3m=inquiries_3m,
        inquiries_6m=inquiries_6m,
        inquiries_12m=inquiries_12m,
        days_since_last_inquiry=days_since_last_inquiry,
        has_term_loan=ContractType.TERM_LOAN in active_types,
        has_mortgage=ContractType.MORTGAGE in active_types,
        has_auto_loan=ContractType.AUTO_LOAN in active_types,
        has_credit_card=ContractType.CREDIT_CARD in active_types,
        has_overdraft=ContractType.OVERDRAFT in active_types,
        has_business_loan=ContractType.BUSINESS_LOAN in active_types,
        dti_ratio=dti_ratio,
    )


__all__ = ["FeatureVector", "extract"]
