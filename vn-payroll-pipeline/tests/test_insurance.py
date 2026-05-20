"""SHUI insurance calculations."""

from __future__ import annotations

import pytest

from payroll.insurance import (
    EMPLOYEE_TOTAL_BPS,
    EMPLOYER_TOTAL_BPS,
    compute_insurance,
    min_wage_for,
    shui_cap_bhtn_for,
    shui_cap_bhxh_bhyt_vnd,
)
from payroll.schema import Region


def test_employee_rate_total_10_5_percent() -> None:
    """Employee SHUI = 8% + 1.5% + 1% = 10.5%."""
    assert EMPLOYEE_TOTAL_BPS == 1_050


def test_employer_rate_total_21_5_percent() -> None:
    """Employer SHUI = 17.5% + 3% + 1% = 21.5%."""
    assert EMPLOYER_TOTAL_BPS == 2_150


def test_compute_insurance_10m_salary() -> None:
    """10M VND salary → 1.05M employee + 2.15M employer."""
    ins = compute_insurance(10_000_000, Region.REGION_1)
    assert ins.employee_total_vnd == 1_050_000
    assert ins.employer_total_vnd == 2_150_000


def test_compute_insurance_below_cap() -> None:
    """Salary at the cap is fully contributable."""
    cap = shui_cap_bhxh_bhyt_vnd()
    ins = compute_insurance(cap, Region.REGION_1)
    # BHXH base equals salary (no truncation).
    assert ins.salary_for_bhxh_vnd == cap


def test_compute_insurance_above_cap() -> None:
    """Salary above 20× region-1 min wage caps BHXH+BHYT contributions."""
    cap = shui_cap_bhxh_bhyt_vnd()
    ins = compute_insurance(cap + 100_000_000, Region.REGION_1)
    assert ins.salary_for_bhxh_vnd == cap


def test_bhtn_region_specific_cap() -> None:
    """BHTN cap uses the employee's region minimum, not region-1."""
    cap_r4 = shui_cap_bhtn_for(Region.REGION_4)
    cap_r1 = shui_cap_bhtn_for(Region.REGION_1)
    assert cap_r4 < cap_r1


def test_compute_insurance_rejects_negative() -> None:
    with pytest.raises(ValueError):
        compute_insurance(-1, Region.REGION_1)


def test_min_wage_ordering() -> None:
    """Region 1 ≥ 2 ≥ 3 ≥ 4."""
    r1 = min_wage_for(Region.REGION_1)
    r2 = min_wage_for(Region.REGION_2)
    r3 = min_wage_for(Region.REGION_3)
    r4 = min_wage_for(Region.REGION_4)
    assert r1 >= r2 >= r3 >= r4


def test_min_wage_region_1_value() -> None:
    """NĐ 74/2024 sets region-1 min at 4,960,000 VND/month."""
    assert min_wage_for(Region.REGION_1) == 4_960_000


def test_zero_salary_zero_contributions() -> None:
    ins = compute_insurance(0, Region.REGION_1)
    assert ins.employee_total_vnd == 0
    assert ins.employer_total_vnd == 0
