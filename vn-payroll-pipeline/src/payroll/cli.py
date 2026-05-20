"""``payroll`` CLI — compute payslips + inspect tax/insurance schedules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from payroll import __version__

    print(f"vn-payroll-pipeline {__version__}")
    return 0


def cmd_brackets(_args: argparse.Namespace) -> int:
    """List the PIT resident brackets."""
    from payroll.tax import resident_brackets

    print(f"{'TIER':<6} {'UPPER (VND)':>16} {'RATE':>6}")
    for i, b in enumerate(resident_brackets(), 1):
        upper = "∞" if b.upper_bound_vnd is None else f"{b.upper_bound_vnd:,}"
        print(f"{i:<6} {upper:>16} {b.rate_bps / 100:>5.1f}%")
    return 0


def cmd_minwage(args: argparse.Namespace) -> int:
    from payroll.insurance import min_wage_for
    from payroll.schema import Region

    region = Region(args.region)
    payload = {
        "region": region.value,
        "min_wage_vnd": min_wage_for(region),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_compute(args: argparse.Namespace) -> int:
    """Compute a single payslip from CLI arguments."""
    from payroll.engine import compute_payslip
    from payroll.schema import Employee, PayPeriod, Region, ResidencyStatus

    emp = Employee(
        employee_id=args.employee_id,
        full_name=args.name,
        residency=ResidencyStatus(args.residency),
        region=Region(args.region),
        n_dependents=args.dependents,
    )
    per = PayPeriod(
        employee_id=args.employee_id,
        year=args.year,
        month=args.month,
        gross_salary_vnd=args.gross,
    )
    slip = compute_payslip(emp, per)
    payload = {
        "employee_id": slip.employee_id,
        "period_iso": slip.period_iso,
        "gross_salary_vnd": slip.gross_salary_vnd,
        "insurance_employee_vnd": slip.insurance_employee_vnd,
        "taxable_income_vnd": slip.taxable_income_vnd,
        "pit_vnd": slip.pit_vnd,
        "net_pay_vnd": slip.net_pay_vnd,
        "insurance_employer_vnd": slip.insurance_employer_vnd,
        "employer_total_cost_vnd": slip.employer_total_cost_vnd,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from payroll.engine import compute_payslip
    from payroll.io_jsonl import dump_payslips
    from payroll.simulator import generate_employees, generate_periods

    employees = generate_employees(n=args.employees, seed=args.seed)
    by_id = {e.employee_id: e for e in employees}
    periods = generate_periods(
        employees,
        year=args.year,
        n_months=args.months,
        seed=args.seed,
    )
    payslips = [compute_payslip(by_id[p.employee_id], p) for p in periods]
    if args.output:
        Path(args.output).write_text(dump_payslips(payslips), encoding="utf-8")
        print(f"wrote {len(payslips)} payslips to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'emp':<10} {'period':<8} {'gross':>14} {'insurance':>12} "
            f"{'pit':>12} {'net':>14}",
        )
        for s in payslips[: args.show]:
            print(
                f"{s.employee_id:<10} {s.period_iso:<8} "
                f"{s.gross_salary_vnd:>14,} {s.insurance_employee_vnd:>12,} "
                f"{s.pit_vnd:>12,} {s.net_pay_vnd:>14,}",
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="payroll",
        description="VN payroll engine — PIT, SHUI, min wages.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("brackets").set_defaults(func=cmd_brackets)

    mw = sub.add_parser("minwage", help="show minimum wage for a region")
    mw.add_argument(
        "--region", required=True, choices=["REGION_1", "REGION_2", "REGION_3", "REGION_4"]
    )
    mw.set_defaults(func=cmd_minwage)

    cp = sub.add_parser("compute", help="compute a single payslip")
    cp.add_argument("--employee-id", required=True)
    cp.add_argument("--name", default="Employee")
    cp.add_argument("--residency", default="RESIDENT", choices=["RESIDENT", "NON_RESIDENT"])
    cp.add_argument(
        "--region", default="REGION_1", choices=["REGION_1", "REGION_2", "REGION_3", "REGION_4"]
    )
    cp.add_argument("--dependents", type=int, default=0)
    cp.add_argument("--year", type=int, default=2025)
    cp.add_argument("--month", type=int, default=1)
    cp.add_argument("--gross", type=int, required=True)
    cp.set_defaults(func=cmd_compute)

    sim = sub.add_parser("simulate", help="batch payroll over many employees")
    sim.add_argument("--employees", type=int, default=20)
    sim.add_argument("--months", type=int, default=12)
    sim.add_argument("--year", type=int, default=2025)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.add_argument("--show", type=int, default=5)
    sim.set_defaults(func=cmd_simulate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
