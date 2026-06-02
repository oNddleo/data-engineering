"""Synthetic VN payroll-data generator."""

from __future__ import annotations

import random

from payroll.schema import Employee, PayPeriod, Region, ResidencyStatus


def generate_employees(
    *,
    n: int = 20,
    seed: int = 0,
) -> list[Employee]:
    """Generate ``n`` employees across regions + residency mix."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    regions = list(Region)
    region_weights = [40, 25, 20, 15]  # rough VN workforce mix
    out: list[Employee] = []
    for i in range(n):
        residency = (
            ResidencyStatus.NON_RESIDENT if rng.random() < 0.05 else ResidencyStatus.RESIDENT
        )
        out.append(
            Employee(
                employee_id=f"E-{i:05d}",
                full_name=f"Employee {i}",
                residency=residency,
                region=rng.choices(regions, weights=region_weights, k=1)[0],
                n_dependents=rng.choices([0, 1, 2, 3], weights=[40, 30, 20, 10], k=1)[0],
            )
        )
    return out


def generate_periods(
    employees: list[Employee],
    *,
    year: int = 2025,
    n_months: int = 12,
    seed: int = 0,
) -> list[PayPeriod]:
    """Generate monthly pay periods for each employee with log-normal gross."""
    if n_months < 1 or n_months > 12:
        raise ValueError("n_months must be in [1, 12]")
    rng = random.Random(seed)
    import math

    out: list[PayPeriod] = []
    for emp in employees:
        # Log-normal centred around 15M-30M VND/month.
        base = int(math.exp(rng.normalvariate(16.8, 0.6)))
        for m in range(1, n_months + 1):
            # Modest month-over-month drift.
            drift = rng.uniform(0.95, 1.05)
            gross = max(0, int(base * drift))
            out.append(
                PayPeriod(
                    employee_id=emp.employee_id,
                    year=year,
                    month=m,
                    gross_salary_vnd=gross,
                )
            )
    return out


__all__ = ["generate_employees", "generate_periods"]
