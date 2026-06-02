"""``evn`` CLI — billing, aggregation, anomaly detection, tariff inspection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from evn import __version__

    print(f"vn-utility-meter-pipeline {__version__}")
    return 0


def cmd_units(_args: argparse.Namespace) -> int:
    """List bundled EVN provincial units."""
    from evn.customer import all_units

    print(f"{'PFX':<4} {'ABBR':<10} {'NAME':<40} {'COVERAGE':<35}")
    for u in all_units():
        print(
            f"{u.prefix:<4} {u.abbreviation:<10} {u.name_en[:40]:<40} " f"{u.coverage_vi[:35]:<35}",
        )
    return 0


def cmd_tariff(args: argparse.Namespace) -> int:
    """Print the household tariff schedule effective on a date."""
    from datetime import date as date_cls

    from evn.tariff import tariff_for_date

    d = date_cls.fromisoformat(args.date) if args.date else date_cls.today()
    sched = tariff_for_date(d)
    payload: dict[str, object] = {
        "date": d.isoformat(),
        "effective_from": sched.effective_from.isoformat(),
        "decision": sched.decision,
        "household_tiers": [
            {
                "tier": i + 1,
                "upper_bound_kwh": t.upper_bound_kwh,
                "vnd_per_kwh": t.vnd_per_kwh,
            }
            for i, t in enumerate(sched.household.tiers)
        ],
        "business_vnd_per_kwh": sched.business.vnd_per_kwh,
        "admin_public_vnd_per_kwh": sched.admin_public.vnd_per_kwh,
        "production_vnd_per_kwh": sched.production.vnd_per_kwh,
        "agriculture_vnd_per_kwh": sched.agriculture.vnd_per_kwh,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from evn.io_jsonl import dump_readings
    from evn.simulator import generate

    readings = generate(
        n_customers=args.customers,
        n_months=args.months,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_readings(readings), encoding="utf-8")
        print(
            f"wrote {len(readings)} readings to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_readings(readings))
    return 0


def cmd_bill(args: argparse.Namespace) -> int:
    """Compute bills for every reading in a JSONL file."""
    from evn.billing import compute_bill
    from evn.io_jsonl import dump_bills, load_readings

    readings = load_readings(Path(args.input).read_text(encoding="utf-8"))
    bills = [compute_bill(r) for r in readings]
    if args.output:
        Path(args.output).write_text(dump_bills(bills), encoding="utf-8")
        print(f"wrote {len(bills)} bills to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'customer':<15} {'cat':<13} {'period':<11} "
            f"{'kwh':>5} {'pre_vat':>14} {'total':>14}",
        )
        for b in bills[: args.show]:
            print(
                f"{b.customer_code:<15} {b.category.value:<13} "
                f"{b.period_start.isoformat():<11} {b.kwh_used:>5} "
                f"{b.pre_vat_amount_vnd:>14,} {b.total_amount_vnd:>14,}",
            )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from evn.aggregator import aggregate_annual
    from evn.billing import compute_bill
    from evn.io_jsonl import dump_summaries, load_readings

    readings = load_readings(Path(args.input).read_text(encoding="utf-8"))
    bills = [compute_bill(r) for r in readings]
    summaries = aggregate_annual(bills)
    if args.output:
        Path(args.output).write_text(
            dump_summaries(summaries),
            encoding="utf-8",
        )
        print(
            f"wrote {len(summaries)} annual summaries to {args.output}",
            file=sys.stderr,
        )
    if args.show:
        print(
            f"{'customer':<15} {'cat':<13} {'#bills':>7} " f"{'total_kwh':>10} {'total_vnd':>14}",
        )
        for s in summaries[: args.show]:
            print(
                f"{s.customer_code:<15} {s.category.value:<13} "
                f"{s.n_bills:>7} {s.total_kwh:>10} "
                f"{s.total_amount_vnd:>14,}",
            )
    return 0


def cmd_anomaly(args: argparse.Namespace) -> int:
    from evn.anomaly import (
        find_sudden_drops,
        find_unrealistic_spikes,
        find_zero_usage,
    )
    from evn.io_jsonl import load_readings

    readings = load_readings(Path(args.input).read_text(encoding="utf-8"))
    zero = find_zero_usage(readings)
    drop = find_sudden_drops(readings)
    spike = find_unrealistic_spikes(readings)
    print(f"ZERO_USAGE ({len(zero)}):")
    for f in zero[: args.show]:
        print(f"  {f.customer_code:<15} {f.category.value:<13} {f.detail}")
    print(f"SUDDEN_DROP ({len(drop)}):")
    for f in drop[: args.show]:
        print(f"  {f.customer_code:<15} {f.category.value:<13} {f.detail}")
    print(f"UNREALISTIC_SPIKE ({len(spike)}):")
    for f in spike[: args.show]:
        print(f"  {f.customer_code:<15} {f.category.value:<13} {f.detail}")
    return 0 if not (zero or drop or spike) else 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="evn",
        description="VN electricity meter pipeline — EVN tariff + billing + anomalies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("units").set_defaults(func=cmd_units)

    tf = sub.add_parser("tariff", help="show the tariff schedule for a date")
    tf.add_argument("--date", default=None, help="ISO YYYY-MM-DD; today() by default")
    tf.set_defaults(func=cmd_tariff)

    sim = sub.add_parser("simulate", help="emit a synthetic meter-reading stream")
    sim.add_argument("--customers", type=int, default=50)
    sim.add_argument("--months", type=int, default=12)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    bl = sub.add_parser("bill", help="compute bills for a reading file")
    bl.add_argument("--input", required=True)
    bl.add_argument("--output", default=None)
    bl.add_argument("--show", type=int, default=10)
    bl.set_defaults(func=cmd_bill)

    sm = sub.add_parser("summary", help="annual per-customer summary")
    sm.add_argument("--input", required=True)
    sm.add_argument("--output", default=None)
    sm.add_argument("--show", type=int, default=10)
    sm.set_defaults(func=cmd_summary)

    an = sub.add_parser("anomaly", help="detect zero / drop / spike anomalies")
    an.add_argument("--input", required=True)
    an.add_argument("--show", type=int, default=5)
    an.set_defaults(func=cmd_anomaly)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
