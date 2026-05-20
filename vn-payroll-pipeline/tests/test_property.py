"""Hypothesis property tests for payroll invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from payroll.engine import compute_payslip
from payroll.insurance import (
    EMPLOYEE_TOTAL_BPS,
    EMPLOYER_TOTAL_BPS,
    compute_insurance,
    shui_cap_bhxh_bhyt_vnd,
)
from payroll.io_jsonl import payslip_from_dict, payslip_to_dict
from payroll.schema import Employee, PayPeriod, Region, ResidencyStatus
from payroll.tax import compute_pit


@given(st.integers(min_value=0, max_value=500_000_000))
def test_employee_insurance_always_le_10_5_pct(gross: int) -> None:
    """Employee SHUI is always ≤ 10.5% of gross (cap can lower it)."""
    ins = compute_insurance(gross, Region.REGION_1)
    assert ins.employee_total_vnd <= gross * EMPLOYEE_TOTAL_BPS // 10_000 + 5


@given(st.integers(min_value=0, max_value=500_000_000))
def test_employer_insurance_always_le_21_5_pct(gross: int) -> None:
    """Employer SHUI is always ≤ 21.5% of gross."""
    ins = compute_insurance(gross, Region.REGION_1)
    assert ins.employer_total_vnd <= gross * EMPLOYER_TOTAL_BPS // 10_000 + 5


@given(st.integers(min_value=0, max_value=500_000_000))
def test_insurance_above_cap_constant(gross: int) -> None:
    """Above the cap, insurance plateau is independent of gross growth."""
    cap = shui_cap_bhxh_bhyt_vnd()
    if gross <= cap:
        return
    ins_at_cap = compute_insurance(cap, Region.REGION_1)
    ins_above = compute_insurance(gross, Region.REGION_1)
    # BHXH + BHYT parts plateau; only BHTN can differ (region-specific cap).
    assert ins_above.bhxh_employee_vnd == ins_at_cap.bhxh_employee_vnd
    assert ins_above.bhyt_employee_vnd == ins_at_cap.bhyt_employee_vnd


@given(
    st.integers(min_value=0, max_value=500_000_000),
    st.integers(min_value=0, max_value=5),
)
@settings(max_examples=80)
def test_pit_with_more_dependents_le_pit_with_fewer(
    gross: int,
    n_dep: int,
) -> None:
    """More dependents → lower (or equal) PIT for residents."""
    pit_more, _ = compute_pit(
        gross_vnd=gross,
        insurance_employee_vnd=0,
        n_dependents=n_dep + 1,
        residency=ResidencyStatus.RESIDENT,
    )
    pit_fewer, _ = compute_pit(
        gross_vnd=gross,
        insurance_employee_vnd=0,
        n_dependents=n_dep,
        residency=ResidencyStatus.RESIDENT,
    )
    assert pit_more <= pit_fewer


@given(st.integers(min_value=0, max_value=80_000_000))
@settings(max_examples=60)
def test_pit_resident_le_non_resident_low_income(gross: int) -> None:
    """At low/mid income (gross ≤ 80M), resident PIT ≤ non-resident PIT.

    Above 80M taxable (~91M gross with default deductions) the resident's
    35% top-bracket marginal rate starts to exceed the non-resident's
    flat 20%, so the property only holds below the crossover.
    """
    res, _ = compute_pit(
        gross_vnd=gross,
        insurance_employee_vnd=0,
        n_dependents=0,
        residency=ResidencyStatus.RESIDENT,
    )
    non, _ = compute_pit(
        gross_vnd=gross,
        insurance_employee_vnd=0,
        n_dependents=0,
        residency=ResidencyStatus.NON_RESIDENT,
    )
    assert res <= non + 10  # tiny tolerance for ceil-rounding drift


@given(
    st.integers(min_value=0, max_value=200_000_000),
    st.sampled_from(list(Region)),
    st.integers(min_value=0, max_value=5),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_payslip_conservation(gross: int, region: Region, n_dep: int) -> None:
    """gross == net + insurance_employee + pit."""
    emp = Employee(
        employee_id="E",
        full_name="x",
        residency=ResidencyStatus.RESIDENT,
        region=region,
        n_dependents=n_dep,
    )
    per = PayPeriod(
        employee_id="E",
        year=2025,
        month=1,
        gross_salary_vnd=gross,
    )
    slip = compute_payslip(emp, per)
    assert slip.gross_salary_vnd == (slip.net_pay_vnd + slip.insurance_employee_vnd + slip.pit_vnd)


@given(
    st.integers(min_value=0, max_value=200_000_000),
    st.sampled_from(list(Region)),
)
@settings(max_examples=50)
def test_payslip_jsonl_roundtrip(gross: int, region: Region) -> None:
    emp = Employee(
        employee_id="E",
        full_name="x",
        residency=ResidencyStatus.RESIDENT,
        region=region,
    )
    per = PayPeriod(
        employee_id="E",
        year=2025,
        month=6,
        gross_salary_vnd=gross,
    )
    slip = compute_payslip(emp, per)
    assert payslip_from_dict(payslip_to_dict(slip)) == slip
