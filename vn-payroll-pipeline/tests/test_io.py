"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from payroll.engine import compute_payslip
from payroll.io_jsonl import (
    dump_employees,
    dump_payslips,
    dump_periods,
    employee_from_dict,
    employee_to_dict,
    load_employees,
    load_payslips,
    load_periods,
    payslip_from_dict,
    payslip_to_dict,
    period_from_dict,
    period_to_dict,
)
from payroll.schema import Employee, PayPeriod, Region, ResidencyStatus


def _employee() -> Employee:
    return Employee(
        employee_id="E-1",
        full_name="Test",
        residency=ResidencyStatus.RESIDENT,
        region=Region.REGION_1,
        n_dependents=2,
    )


def _period() -> PayPeriod:
    return PayPeriod(
        employee_id="E-1",
        year=2025,
        month=5,
        gross_salary_vnd=30_000_000,
    )


def test_employee_roundtrip() -> None:
    e = _employee()
    assert employee_from_dict(employee_to_dict(e)) == e


def test_period_roundtrip() -> None:
    p = _period()
    assert period_from_dict(period_to_dict(p)) == p


def test_payslip_roundtrip() -> None:
    slip = compute_payslip(_employee(), _period())
    assert payslip_from_dict(payslip_to_dict(slip)) == slip


def test_dump_load_many() -> None:
    emps = [
        Employee(
            employee_id=f"E-{i}",
            full_name=f"Person {i}",
            residency=ResidencyStatus.RESIDENT,
            region=Region.REGION_2,
            n_dependents=i % 3,
        )
        for i in range(5)
    ]
    assert load_employees(dump_employees(emps)) == emps


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_employees("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    bad = '{"employee_id": 1, "full_name": "x", "residency": "RESIDENT", "region": "REGION_1", "n_dependents": 0}\n'
    with pytest.raises(TypeError):
        load_employees(bad)


def test_dump_periods_skips_blank_lines() -> None:
    periods = [_period()]
    text = "\n\n" + dump_periods(periods) + "\n\n"
    assert load_periods(text) == periods


def test_dump_payslips_empty() -> None:
    assert load_payslips(dump_payslips([])) == []
