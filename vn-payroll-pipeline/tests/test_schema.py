"""Schema validation for Employee / PayPeriod / Payslip."""

from __future__ import annotations

import pytest

from payroll.schema import (
    Employee,
    PayPeriod,
    Payslip,
    Region,
    ResidencyStatus,
)


def test_employee_basic() -> None:
    e = Employee(
        employee_id="E-1",
        full_name="Test Person",
        residency=ResidencyStatus.RESIDENT,
        region=Region.REGION_1,
        n_dependents=2,
    )
    assert e.n_dependents == 2


def test_employee_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="employee_id"):
        Employee(
            employee_id="",
            full_name="x",
            residency=ResidencyStatus.RESIDENT,
            region=Region.REGION_1,
        )


def test_employee_rejects_negative_dependents() -> None:
    with pytest.raises(ValueError, match="n_dependents"):
        Employee(
            employee_id="E-1",
            full_name="x",
            residency=ResidencyStatus.RESIDENT,
            region=Region.REGION_1,
            n_dependents=-1,
        )


def test_period_basic() -> None:
    p = PayPeriod(
        employee_id="E-1",
        year=2025,
        month=5,
        gross_salary_vnd=20_000_000,
    )
    assert p.period_iso == "2025-05"


def test_period_rejects_invalid_month() -> None:
    with pytest.raises(ValueError, match="month"):
        PayPeriod(employee_id="E-1", year=2025, month=13, gross_salary_vnd=0)


def test_period_rejects_old_year() -> None:
    with pytest.raises(ValueError, match="year"):
        PayPeriod(employee_id="E-1", year=1999, month=1, gross_salary_vnd=0)


def test_period_rejects_negative_gross() -> None:
    with pytest.raises(ValueError):
        PayPeriod(employee_id="E-1", year=2025, month=1, gross_salary_vnd=-1)


def test_residency_complete() -> None:
    assert {r.value for r in ResidencyStatus} == {"RESIDENT", "NON_RESIDENT"}


def test_regions_complete() -> None:
    assert {r.value for r in Region} == {
        "REGION_1",
        "REGION_2",
        "REGION_3",
        "REGION_4",
    }


def test_payslip_rejects_negative() -> None:
    with pytest.raises(ValueError, match="pit_vnd"):
        Payslip(
            employee_id="E-1",
            period_iso="2025-01",
            gross_salary_vnd=10_000_000,
            insurance_employee_vnd=1_000_000,
            taxable_income_vnd=0,
            pit_vnd=-1,
            net_pay_vnd=9_000_000,
            insurance_employer_vnd=2_000_000,
            employer_total_cost_vnd=12_000_000,
        )
