"""Payroll engine — turns ``(Employee, PayPeriod)`` into a ``Payslip``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from payroll.insurance import compute_insurance
from payroll.schema import Payslip
from payroll.tax import compute_pit

if TYPE_CHECKING:
    from payroll.schema import Employee, PayPeriod


def compute_payslip(employee: Employee, period: PayPeriod) -> Payslip:
    """Run one monthly payroll calculation."""
    if employee.employee_id != period.employee_id:
        raise ValueError(
            f"employee_id mismatch: employee={employee.employee_id} "
            f"vs period={period.employee_id}",
        )

    ins = compute_insurance(period.gross_salary_vnd, employee.region)
    pit, taxable = compute_pit(
        gross_vnd=period.gross_salary_vnd,
        insurance_employee_vnd=ins.employee_total_vnd,
        n_dependents=employee.n_dependents,
        residency=employee.residency,
    )

    net = period.gross_salary_vnd - ins.employee_total_vnd - pit
    if net < 0:
        # Defensive — should never trigger because brackets are progressive
        # and insurance < gross, but clamp to avoid negative payroll output.
        net = 0
    employer_total = period.gross_salary_vnd + ins.employer_total_vnd

    return Payslip(
        employee_id=employee.employee_id,
        period_iso=period.period_iso,
        gross_salary_vnd=period.gross_salary_vnd,
        insurance_employee_vnd=ins.employee_total_vnd,
        taxable_income_vnd=taxable,
        pit_vnd=pit,
        net_pay_vnd=net,
        insurance_employer_vnd=ins.employer_total_vnd,
        employer_total_cost_vnd=employer_total,
    )


__all__ = ["compute_payslip"]
