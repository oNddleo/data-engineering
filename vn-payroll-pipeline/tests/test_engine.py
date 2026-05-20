"""Payroll engine end-to-end."""

from __future__ import annotations

import pytest

from payroll.engine import compute_payslip
from payroll.schema import Employee, PayPeriod, Region, ResidencyStatus


def _employee(**overrides: object) -> Employee:
    defaults = {
        "employee_id": "E-1",
        "full_name": "Test Person",
        "residency": ResidencyStatus.RESIDENT,
        "region": Region.REGION_1,
        "n_dependents": 0,
    }
    defaults.update(overrides)
    return Employee(**defaults)  # type: ignore[arg-type]


def _period(**overrides: object) -> PayPeriod:
    defaults = {
        "employee_id": "E-1",
        "year": 2025,
        "month": 1,
        "gross_salary_vnd": 30_000_000,
    }
    defaults.update(overrides)
    return PayPeriod(**defaults)  # type: ignore[arg-type]


def test_payslip_basic_resident() -> None:
    slip = compute_payslip(_employee(), _period())
    assert slip.gross_salary_vnd == 30_000_000
    # 30M × 10.5% = 3.15M insurance.
    assert slip.insurance_employee_vnd == 3_150_000
    # Net = gross - insurance - PIT.
    assert slip.net_pay_vnd == slip.gross_salary_vnd - slip.insurance_employee_vnd - slip.pit_vnd


def test_payslip_with_dependents_lowers_pit() -> None:
    no_dep = compute_payslip(_employee(n_dependents=0), _period())
    with_dep = compute_payslip(_employee(n_dependents=2), _period())
    assert with_dep.pit_vnd < no_dep.pit_vnd


def test_payslip_non_resident_higher_pit() -> None:
    """Non-residents pay 20% flat → higher PIT than equivalent resident."""
    resident = compute_payslip(_employee(), _period(gross_salary_vnd=20_000_000))
    nonresident = compute_payslip(
        _employee(residency=ResidencyStatus.NON_RESIDENT),
        _period(gross_salary_vnd=20_000_000),
    )
    assert nonresident.pit_vnd > resident.pit_vnd


def test_payslip_employer_cost_includes_insurance() -> None:
    slip = compute_payslip(_employee(), _period())
    assert slip.employer_total_cost_vnd == slip.gross_salary_vnd + slip.insurance_employer_vnd


def test_payslip_zero_gross_no_tax() -> None:
    slip = compute_payslip(_employee(), _period(gross_salary_vnd=0))
    assert slip.pit_vnd == 0
    assert slip.net_pay_vnd == 0


def test_payslip_rejects_employee_mismatch() -> None:
    """Period employee_id must match employee.employee_id."""
    with pytest.raises(ValueError, match="employee_id mismatch"):
        compute_payslip(_employee(employee_id="E-1"), _period(employee_id="E-2"))


def test_payslip_high_earner_top_bracket() -> None:
    """At 200M VND/month, taxable hits the 35% top bracket."""
    slip = compute_payslip(_employee(), _period(gross_salary_vnd=200_000_000))
    # The marginal taxable amount in the top bracket pays 35%.
    assert slip.pit_vnd > 30_000_000


def test_payslip_region_affects_bhtn_cap() -> None:
    """A very-high earner in REGION_4 has a lower BHTN cap than REGION_1."""
    salary = 200_000_000
    r1 = compute_payslip(_employee(region=Region.REGION_1), _period(gross_salary_vnd=salary))
    r4 = compute_payslip(_employee(region=Region.REGION_4), _period(gross_salary_vnd=salary))
    # REGION_4 has a lower BHTN cap → lower employee insurance.
    assert r4.insurance_employee_vnd < r1.insurance_employee_vnd
