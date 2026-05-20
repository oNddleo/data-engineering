"""VN payroll schema — employee + payroll period + payslip.

Models the entities for a Vietnamese monthly payroll run:

* ``Employee`` — basic identity, residency status, dependents count.
* ``PayPeriod`` — one calendar month for one employee.
* ``Payslip`` — the computed take-home + tax + insurance + employer cost.

All money is **integer VND**. Resident vs non-resident distinction
matters: non-residents pay a flat 20% PIT on all VN-sourced income
(Article 18 Luật Thuế TNCN), while residents follow the 7-bracket
progressive schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ResidencyStatus(str, Enum):
    """Two PIT residency classes."""

    RESIDENT = "RESIDENT"  # ≥183 days in VN per year
    NON_RESIDENT = "NON_RESIDENT"  # flat 20% PIT


class Region(str, Enum):
    """Four regional minimum-wage zones (Nghị định 38/2022/NĐ-CP)."""

    REGION_1 = "REGION_1"  # HCMC, Hanoi inner districts
    REGION_2 = "REGION_2"  # tier-2 cities (Hai Phong, Da Nang, Can Tho)
    REGION_3 = "REGION_3"  # provincial capitals
    REGION_4 = "REGION_4"  # rural districts


@dataclass(frozen=True, slots=True)
class Employee:
    """One employee record."""

    employee_id: str
    full_name: str
    residency: ResidencyStatus
    region: Region
    n_dependents: int = 0  # number of registered NPT (người phụ thuộc)

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not self.full_name:
            raise ValueError("full_name must be non-empty")
        if self.n_dependents < 0:
            raise ValueError(
                f"n_dependents must be >= 0, got {self.n_dependents}",
            )


@dataclass(frozen=True, slots=True)
class PayPeriod:
    """One monthly pay period for one employee."""

    employee_id: str
    year: int
    month: int  # 1-12
    gross_salary_vnd: int  # contractual gross (lương cơ bản + phụ cấp)

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty")
        if not (1 <= self.month <= 12):
            raise ValueError(f"month must be in [1, 12], got {self.month}")
        if self.year < 2000:
            raise ValueError(f"year must be >= 2000, got {self.year}")
        if self.gross_salary_vnd < 0:
            raise ValueError("gross_salary_vnd must be >= 0")

    @property
    def period_iso(self) -> str:
        """``YYYY-MM`` form for indexing."""
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def period_date(self) -> date:
        """First day of the month."""
        return date(self.year, self.month, 1)


@dataclass(frozen=True, slots=True)
class Payslip:
    """Computed payroll output for one ``PayPeriod``."""

    employee_id: str
    period_iso: str

    gross_salary_vnd: int  # input
    insurance_employee_vnd: int  # SHUI deducted from employee
    taxable_income_vnd: int  # gross − insurance − deductions
    pit_vnd: int  # personal income tax
    net_pay_vnd: int  # gross − insurance − PIT

    insurance_employer_vnd: int  # employer-side SHUI contribution
    employer_total_cost_vnd: int  # gross + employer insurance

    def __post_init__(self) -> None:
        for name in (
            "gross_salary_vnd",
            "insurance_employee_vnd",
            "taxable_income_vnd",
            "pit_vnd",
            "net_pay_vnd",
            "insurance_employer_vnd",
            "employer_total_cost_vnd",
        ):
            val = getattr(self, name)
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")


__all__ = [
    "Employee",
    "PayPeriod",
    "Payslip",
    "Region",
    "ResidencyStatus",
]
