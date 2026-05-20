"""SHUI insurance contribution rates (2025 schedule).

Vietnamese social-insurance package is **SHUI** — Social, Health,
Unemployment Insurance — split between employee and employer per
Decree 12/2025/NĐ-CP and Decree 58/2020/NĐ-CP:

| Fund     | Employee | Employer | Combined |
| -------- | -------- | -------- | -------- |
| BHXH     | 8.0%     | 17.5%    | 25.5%    |
| BHYT     | 1.5%     | 3.0%     | 4.5%     |
| BHTN     | 1.0%     | 1.0%     | 2.0%     |
| **Total**| **10.5%**| **21.5%**| **32.0%**|

Contributions are capped at **20× region-1 minimum monthly wage**
for BHXH + BHYT (Article 89 Luật BHXH 2014) and **20× region-specific
minimum wage** for BHTN (Article 58 Luật Việc Làm 2013).

Region-1 minimum wage (Nghị định 74/2024/NĐ-CP effective 2024-07-01):
**4,960,000 VND/month** → BHXH+BHYT cap = ``99,200,000 VND``.
"""

from __future__ import annotations

from dataclasses import dataclass

from payroll.schema import Region

# Contribution rates in basis points (10_000 = 100%).
BHXH_EMPLOYEE_BPS = 800  # 8%
BHYT_EMPLOYEE_BPS = 150  # 1.5%
BHTN_EMPLOYEE_BPS = 100  # 1%
EMPLOYEE_TOTAL_BPS = BHXH_EMPLOYEE_BPS + BHYT_EMPLOYEE_BPS + BHTN_EMPLOYEE_BPS

BHXH_EMPLOYER_BPS = 1_750  # 17.5%
BHYT_EMPLOYER_BPS = 300  # 3%
BHTN_EMPLOYER_BPS = 100  # 1%
EMPLOYER_TOTAL_BPS = BHXH_EMPLOYER_BPS + BHYT_EMPLOYER_BPS + BHTN_EMPLOYER_BPS

# Region-1 base wage used for SHUI cap (NĐ 74/2024/NĐ-CP).
REGION_1_MIN_WAGE_VND = 4_960_000
SHUI_CAP_MULTIPLIER = 20

# Regional minimum wages, all monthly (NĐ 74/2024/NĐ-CP).
_REGION_MIN_WAGES: dict[Region, int] = {
    Region.REGION_1: 4_960_000,
    Region.REGION_2: 4_410_000,
    Region.REGION_3: 3_860_000,
    Region.REGION_4: 3_450_000,
}


@dataclass(frozen=True, slots=True)
class InsuranceBreakdown:
    """Employee + employer SHUI contributions for one month."""

    salary_for_bhxh_vnd: int  # capped at 20× region-1 min
    salary_for_bhtn_vnd: int  # capped at 20× region-specific min

    bhxh_employee_vnd: int
    bhyt_employee_vnd: int
    bhtn_employee_vnd: int
    employee_total_vnd: int

    bhxh_employer_vnd: int
    bhyt_employer_vnd: int
    bhtn_employer_vnd: int
    employer_total_vnd: int


def min_wage_for(region: Region) -> int:
    """Return the monthly minimum wage for ``region``."""
    return _REGION_MIN_WAGES[region]


def shui_cap_bhxh_bhyt_vnd() -> int:
    """Cap on the contribution base for BHXH + BHYT."""
    return REGION_1_MIN_WAGE_VND * SHUI_CAP_MULTIPLIER


def shui_cap_bhtn_for(region: Region) -> int:
    """Cap on the contribution base for BHTN (region-specific)."""
    return min_wage_for(region) * SHUI_CAP_MULTIPLIER


def compute_insurance(
    gross_salary_vnd: int,
    region: Region,
) -> InsuranceBreakdown:
    """Compute SHUI for one month given ``gross_salary_vnd`` and ``region``."""
    if gross_salary_vnd < 0:
        raise ValueError(
            f"gross_salary_vnd must be >= 0, got {gross_salary_vnd}",
        )

    base_bhxh = min(gross_salary_vnd, shui_cap_bhxh_bhyt_vnd())
    base_bhtn = min(gross_salary_vnd, shui_cap_bhtn_for(region))

    bhxh_emp = (base_bhxh * BHXH_EMPLOYEE_BPS) // 10_000
    bhyt_emp = (base_bhxh * BHYT_EMPLOYEE_BPS) // 10_000
    bhtn_emp = (base_bhtn * BHTN_EMPLOYEE_BPS) // 10_000

    bhxh_er = (base_bhxh * BHXH_EMPLOYER_BPS) // 10_000
    bhyt_er = (base_bhxh * BHYT_EMPLOYER_BPS) // 10_000
    bhtn_er = (base_bhtn * BHTN_EMPLOYER_BPS) // 10_000

    return InsuranceBreakdown(
        salary_for_bhxh_vnd=base_bhxh,
        salary_for_bhtn_vnd=base_bhtn,
        bhxh_employee_vnd=bhxh_emp,
        bhyt_employee_vnd=bhyt_emp,
        bhtn_employee_vnd=bhtn_emp,
        employee_total_vnd=bhxh_emp + bhyt_emp + bhtn_emp,
        bhxh_employer_vnd=bhxh_er,
        bhyt_employer_vnd=bhyt_er,
        bhtn_employer_vnd=bhtn_er,
        employer_total_vnd=bhxh_er + bhyt_er + bhtn_er,
    )


__all__ = [
    "BHTN_EMPLOYEE_BPS",
    "BHTN_EMPLOYER_BPS",
    "BHXH_EMPLOYEE_BPS",
    "BHXH_EMPLOYER_BPS",
    "BHYT_EMPLOYEE_BPS",
    "BHYT_EMPLOYER_BPS",
    "EMPLOYEE_TOTAL_BPS",
    "EMPLOYER_TOTAL_BPS",
    "InsuranceBreakdown",
    "REGION_1_MIN_WAGE_VND",
    "SHUI_CAP_MULTIPLIER",
    "compute_insurance",
    "min_wage_for",
    "shui_cap_bhtn_for",
    "shui_cap_bhxh_bhyt_vnd",
]
