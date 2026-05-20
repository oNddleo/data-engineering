"""Personal Income Tax (PIT / Thuế TNCN) computation.

For **residents**, PIT follows a 7-bracket progressive schedule
(Article 22 Luật Thuế TNCN amended by Luật 26/2012/QH13):

| Bracket | Monthly taxable (VND) | Rate |
| ------- | --------------------- | ---- |
| 1       | 0 – 5 000 000         | 5%   |
| 2       | 5M – 10M              | 10%  |
| 3       | 10M – 18M             | 15%  |
| 4       | 18M – 32M             | 20%  |
| 5       | 32M – 52M             | 25%  |
| 6       | 52M – 80M             | 30%  |
| 7       | > 80M                 | 35%  |

For **non-residents**, PIT is a flat 20% of VN-sourced income
(Article 18). No bracket progression, no personal/dependent deduction.

Personal deductions (Nghị quyết 954/2020/UBTVQH14):

* Personal allowance (giảm trừ bản thân): **11,000,000 VND/month**
* Per dependent (giảm trừ NPT): **4,400,000 VND/month**

We deduct insurance + personal allowance + dependent allowance to
arrive at **taxable income**, then apply the bracket schedule.
"""

from __future__ import annotations

from dataclasses import dataclass

from payroll.schema import ResidencyStatus

# Personal deductions (Nghị quyết 954/2020/UBTVQH14).
PERSONAL_ALLOWANCE_VND = 11_000_000
DEPENDENT_ALLOWANCE_VND = 4_400_000

# Non-resident flat rate.
NON_RESIDENT_RATE_BPS = 2_000  # 20%


@dataclass(frozen=True, slots=True)
class PITBracket:
    """One progressive PIT bracket."""

    upper_bound_vnd: int | None  # None → top bracket (open-ended)
    rate_bps: int  # 10_000 = 100%


_RESIDENT_BRACKETS: tuple[PITBracket, ...] = (
    PITBracket(upper_bound_vnd=5_000_000, rate_bps=500),  # 5%
    PITBracket(upper_bound_vnd=10_000_000, rate_bps=1_000),  # 10%
    PITBracket(upper_bound_vnd=18_000_000, rate_bps=1_500),  # 15%
    PITBracket(upper_bound_vnd=32_000_000, rate_bps=2_000),  # 20%
    PITBracket(upper_bound_vnd=52_000_000, rate_bps=2_500),  # 25%
    PITBracket(upper_bound_vnd=80_000_000, rate_bps=3_000),  # 30%
    PITBracket(upper_bound_vnd=None, rate_bps=3_500),  # 35%
)


def resident_brackets() -> tuple[PITBracket, ...]:
    """Return the 7-bracket schedule used for resident PIT."""
    return _RESIDENT_BRACKETS


def taxable_income(
    gross_vnd: int,
    insurance_employee_vnd: int,
    n_dependents: int,
) -> int:
    """Compute monthly taxable income for a resident.

    ``taxable = gross − insurance − personal_allowance − n_dep × dep_allowance``.
    Clamped to ``>= 0``.
    """
    if gross_vnd < 0 or insurance_employee_vnd < 0 or n_dependents < 0:
        raise ValueError("inputs must be >= 0")
    deductions = (
        insurance_employee_vnd + PERSONAL_ALLOWANCE_VND + n_dependents * DEPENDENT_ALLOWANCE_VND
    )
    return max(0, gross_vnd - deductions)


def compute_pit(
    gross_vnd: int,
    insurance_employee_vnd: int,
    n_dependents: int,
    residency: ResidencyStatus,
) -> tuple[int, int]:
    """Compute PIT and the underlying taxable amount.

    Returns ``(pit_vnd, taxable_vnd)``.
    """
    if residency is ResidencyStatus.NON_RESIDENT:
        # Flat 20% on gross (no deductions for non-residents).
        taxable = max(0, gross_vnd)
        pit = (taxable * NON_RESIDENT_RATE_BPS + 9_999) // 10_000
        return pit, taxable

    taxable = taxable_income(gross_vnd, insurance_employee_vnd, n_dependents)
    if taxable == 0:
        return 0, 0

    pit = 0
    remaining = taxable
    lower = 0
    for bracket in _RESIDENT_BRACKETS:
        if remaining <= 0:
            break
        upper = bracket.upper_bound_vnd
        slab = remaining if upper is None else min(remaining, upper - lower)
        if slab <= 0:
            lower = upper if upper is not None else lower
            continue
        pit += (slab * bracket.rate_bps + 9_999) // 10_000
        remaining -= slab
        if upper is None:
            break
        lower = upper
    return pit, taxable


__all__ = [
    "DEPENDENT_ALLOWANCE_VND",
    "NON_RESIDENT_RATE_BPS",
    "PERSONAL_ALLOWANCE_VND",
    "PITBracket",
    "compute_pit",
    "resident_brackets",
    "taxable_income",
]
