"""Seeded synthetic CIC-borrower generator.

The generator builds borrowers with one of three "risk profiles":

* ``"clean"`` — group 1 every month, no inquiries, low DTI.
* ``"watch"`` — bounces between group 1 and 2 mid-window.
* ``"distressed"`` — escalates 1 → 2 → 3 → 4 and gets multiple
  inquiries (credit shopping).

The simulator is the only place we use ``random``; everything else
must be deterministic from the borrower object alone.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from cicscore.cic_groups import group_from_days_past_due
from cicscore.schema import (
    Borrower,
    ContractType,
    CreditContract,
    GroupAssessment,
    Inquiry,
    add_months,
    first_of_month,
)

_BANKS = ("VCB", "BIDV", "TCB", "MB", "VPB", "ACB", "VTB", "AGB", "HDB", "TPB")
RISK_PROFILES = ("clean", "watch", "distressed")


def _make_contract(
    rng: random.Random,
    *,
    borrower_id: str,
    opened_at: date,
    contract_type: ContractType,
    suffix: str,
) -> CreditContract:
    return CreditContract(
        contract_id=f"{borrower_id}-{suffix}",
        borrower_id=borrower_id,
        lender_bank=rng.choice(_BANKS),
        contract_type=contract_type,
        original_amount_vnd=rng.choice([50_000_000, 100_000_000, 200_000_000, 500_000_000]),
        opened_at=opened_at,
        closed_at=None,
    )


def _amortising_principal(original: int, month_idx: int, total_months: int) -> int:
    """Straight-line amortisation — keeps the simulator simple."""
    remaining = max(0, total_months - month_idx)
    return int(original * remaining / total_months)


def _assess(
    *,
    contract: CreditContract,
    as_of_month: date,
    month_idx: int,
    days_past_due: int,
) -> GroupAssessment:
    principal = _amortising_principal(contract.original_amount_vnd, month_idx, total_months=36)
    interest = int(principal * 0.012)  # ~14 % APR / 12 ≈ 1.2 %/month
    group = group_from_days_past_due(days_past_due)
    return GroupAssessment(
        contract_id=contract.contract_id,
        as_of_month=as_of_month,
        group=group,
        outstanding_principal_vnd=principal,
        outstanding_interest_vnd=interest,
        days_past_due=days_past_due,
    )


def _profile_days_past_due(profile: str, month_idx: int) -> int:
    """Return the days-past-due number at ``month_idx`` for the given profile."""
    if profile == "clean":
        return 0
    if profile == "watch":
        # Bounce: 0 / 0 / 30 / 0 / 0 / 30 …
        return 30 if month_idx % 3 == 2 else 0
    if profile == "distressed":
        # Escalate slowly month-by-month past key cutoffs.
        if month_idx < 6:
            return 0
        if month_idx < 12:
            return 30 + (month_idx - 6) * 10  # group 2
        if month_idx < 18:
            return 100 + (month_idx - 12) * 15  # group 3
        return 200 + (month_idx - 18) * 25  # group 4 / 5
    raise ValueError(f"unknown profile {profile!r}")


def generate_borrower(
    rng: random.Random,
    *,
    borrower_id: str,
    profile: str,
    observation_date: date,
    history_months: int = 24,
) -> Borrower:
    """Build one synthetic Borrower covering ``history_months`` ending at obs_date."""
    if profile not in RISK_PROFILES:
        raise ValueError(f"unknown profile {profile!r}; pick one of {RISK_PROFILES}")
    obs_month = first_of_month(observation_date)
    start_month = add_months(obs_month, -(history_months - 1))

    # Two contracts: one TERM_LOAN + one CREDIT_CARD.
    c1 = _make_contract(
        rng,
        borrower_id=borrower_id,
        opened_at=start_month,
        contract_type=ContractType.TERM_LOAN,
        suffix="L",
    )
    c2 = _make_contract(
        rng,
        borrower_id=borrower_id,
        opened_at=add_months(start_month, 3),
        contract_type=ContractType.CREDIT_CARD,
        suffix="C",
    )

    assessments: list[GroupAssessment] = []
    for m in range(history_months):
        month = add_months(start_month, m)
        dpd = _profile_days_past_due(profile, m)
        assessments.append(_assess(contract=c1, as_of_month=month, month_idx=m, days_past_due=dpd))
        if month >= c2.opened_at:
            assessments.append(
                _assess(contract=c2, as_of_month=month, month_idx=m, days_past_due=dpd)
            )

    inquiries: list[Inquiry] = []
    if profile == "distressed":
        for i in range(4):
            inquiries.append(
                Inquiry(
                    borrower_id=borrower_id,
                    lender_bank=rng.choice(_BANKS),
                    inquired_at=observation_date - timedelta(days=15 + i * 30),
                    purpose="NEW_LOAN",
                )
            )
    elif profile == "watch":
        inquiries.append(
            Inquiry(
                borrower_id=borrower_id,
                lender_bank=rng.choice(_BANKS),
                inquired_at=observation_date - timedelta(days=45),
                purpose="NEW_LOAN",
            )
        )

    monthly_income = rng.choice([15_000_000, 25_000_000, 40_000_000])
    if profile == "distressed":
        monthly_income = 8_000_000
    return Borrower(
        borrower_id=borrower_id,
        contracts=(c1, c2),
        assessments=tuple(assessments),
        inquiries=tuple(inquiries),
        monthly_income_vnd=monthly_income,
    )


def generate(
    *,
    n_borrowers: int = 10,
    seed: int = 0,
    observation_date: date | None = None,
    profile_mix: tuple[str, ...] | None = None,
) -> list[Borrower]:
    """Build a population of synthetic borrowers.

    ``profile_mix`` controls the distribution; defaults to roughly
    60 % clean / 25 % watch / 15 % distressed.
    """
    rng = random.Random(seed)
    obs = observation_date or date(2026, 5, 14)
    mix = profile_mix or (
        *(["clean"] * 60),
        *(["watch"] * 25),
        *(["distressed"] * 15),
    )
    return [
        generate_borrower(
            rng,
            borrower_id=f"NB-{i:06d}",
            profile=mix[i % len(mix)],
            observation_date=obs,
        )
        for i in range(n_borrowers)
    ]


__all__ = ["RISK_PROFILES", "generate", "generate_borrower"]
