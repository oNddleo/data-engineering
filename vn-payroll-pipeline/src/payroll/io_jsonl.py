"""JSONL codec for Employee / PayPeriod / Payslip."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from payroll.schema import Employee, PayPeriod, Payslip, Region, ResidencyStatus

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def employee_to_dict(e: Employee) -> dict[str, object]:
    return {
        "employee_id": e.employee_id,
        "full_name": e.full_name,
        "residency": e.residency.value,
        "region": e.region.value,
        "n_dependents": e.n_dependents,
    }


def employee_from_dict(d: dict[str, object]) -> Employee:
    return Employee(
        employee_id=_require_str(d, "employee_id"),
        full_name=_require_str(d, "full_name"),
        residency=ResidencyStatus(_require_str(d, "residency")),
        region=Region(_require_str(d, "region")),
        n_dependents=_require_int(d, "n_dependents"),
    )


def period_to_dict(p: PayPeriod) -> dict[str, object]:
    return {
        "employee_id": p.employee_id,
        "year": p.year,
        "month": p.month,
        "gross_salary_vnd": p.gross_salary_vnd,
    }


def period_from_dict(d: dict[str, object]) -> PayPeriod:
    return PayPeriod(
        employee_id=_require_str(d, "employee_id"),
        year=_require_int(d, "year"),
        month=_require_int(d, "month"),
        gross_salary_vnd=_require_int(d, "gross_salary_vnd"),
    )


def payslip_to_dict(p: Payslip) -> dict[str, object]:
    return {
        "employee_id": p.employee_id,
        "period_iso": p.period_iso,
        "gross_salary_vnd": p.gross_salary_vnd,
        "insurance_employee_vnd": p.insurance_employee_vnd,
        "taxable_income_vnd": p.taxable_income_vnd,
        "pit_vnd": p.pit_vnd,
        "net_pay_vnd": p.net_pay_vnd,
        "insurance_employer_vnd": p.insurance_employer_vnd,
        "employer_total_cost_vnd": p.employer_total_cost_vnd,
    }


def payslip_from_dict(d: dict[str, object]) -> Payslip:
    return Payslip(
        employee_id=_require_str(d, "employee_id"),
        period_iso=_require_str(d, "period_iso"),
        gross_salary_vnd=_require_int(d, "gross_salary_vnd"),
        insurance_employee_vnd=_require_int(d, "insurance_employee_vnd"),
        taxable_income_vnd=_require_int(d, "taxable_income_vnd"),
        pit_vnd=_require_int(d, "pit_vnd"),
        net_pay_vnd=_require_int(d, "net_pay_vnd"),
        insurance_employer_vnd=_require_int(d, "insurance_employer_vnd"),
        employer_total_cost_vnd=_require_int(d, "employer_total_cost_vnd"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_employees(items: Iterable[Employee]) -> str:
    return _dump(employee_to_dict(e) for e in items)


def dump_periods(items: Iterable[PayPeriod]) -> str:
    return _dump(period_to_dict(p) for p in items)


def dump_payslips(items: Iterable[Payslip]) -> str:
    return _dump(payslip_to_dict(p) for p in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_employees(text: str) -> list[Employee]:
    return [employee_from_dict(d) for d in _iter_lines(text)]


def load_periods(text: str) -> list[PayPeriod]:
    return [period_from_dict(d) for d in _iter_lines(text)]


def load_payslips(text: str) -> list[Payslip]:
    return [payslip_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_employees",
    "dump_payslips",
    "dump_periods",
    "employee_from_dict",
    "employee_to_dict",
    "load_employees",
    "load_payslips",
    "load_periods",
    "payslip_from_dict",
    "payslip_to_dict",
    "period_from_dict",
    "period_to_dict",
]
