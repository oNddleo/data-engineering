"""``evnmeter`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from evnmeter import __version__

    print(f"electricity-meter-iot-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from evnmeter.io_jsonl import dump_meters, dump_readings
    from evnmeter.simulator import generate

    meters, readings = generate(
        n_meters=args.meters,
        n_days=args.days,
        gap_fraction=args.gap_fraction,
        out_of_order_fraction=args.out_of_order_fraction,
        rollover_fraction=args.rollover_fraction,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meters.jsonl").write_text(dump_meters(meters), encoding="utf-8")
    (out_dir / "readings.jsonl").write_text(dump_readings(readings), encoding="utf-8")
    print(
        f"wrote {len(meters)} meters + {len(readings)} readings to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_derive(args: argparse.Namespace) -> int:
    from evnmeter.derive import derive
    from evnmeter.io_jsonl import dump_intervals, load_readings

    readings = list(load_readings(Path(args.input).read_text(encoding="utf-8")))
    intervals = derive(readings, max_gap_minutes=args.max_gap_minutes)
    out_text = dump_intervals(intervals)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        n_est = sum(1 for c in intervals if c.is_estimated)
        print(
            f"wrote {len(intervals)} intervals to {args.output} " f"({n_est} estimated from gaps)",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_anomaly(args: argparse.Namespace) -> int:
    from evnmeter.anomaly import find_gaps, find_spikes, find_stuck
    from evnmeter.io_jsonl import load_intervals

    intervals = list(load_intervals(Path(args.input).read_text(encoding="utf-8")))
    gaps = find_gaps(intervals, min_minutes=args.min_gap_minutes)
    spikes = find_spikes(intervals, multiplier=args.spike_multiplier)
    stuck = find_stuck(intervals, min_zero_intervals=args.stuck_intervals)
    print(f"GAPS ({len(gaps)}):")
    for a in gaps[: args.show]:
        print(f"  {a.meter_id:<10} {a.start_at.isoformat()}  {a.detail}")
    print(f"SPIKES ({len(spikes)}):")
    for a in spikes[: args.show]:
        print(f"  {a.meter_id:<10} {a.start_at.isoformat()}  {a.detail}")
    print(f"STUCK ({len(stuck)}):")
    for a in stuck[: args.show]:
        print(f"  {a.meter_id:<10} {a.start_at.isoformat()}  {a.detail}")
    return 0


def cmd_bill(args: argparse.Namespace) -> int:
    from evnmeter.billing import bill_meters
    from evnmeter.io_jsonl import dump_bills, load_intervals

    intervals = list(load_intervals(Path(args.input).read_text(encoding="utf-8")))
    period_start = datetime.fromisoformat(args.period_start)
    period_end = datetime.fromisoformat(args.period_end)
    bills = bill_meters(intervals, period_start, period_end)
    out_text = dump_bills(bills)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(bills)} bills to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'meter':<10} {'kwh':>5} {'subtotal':>12} {'vat':>10} "
            f"{'grand_total':>13} {'est_iv':>7}"
        )
        for b in sorted(bills, key=lambda b: -b.grand_total_vnd)[: args.show]:
            print(
                f"{b.meter_id:<10} {b.billed_kwh:>5} "
                f"{b.subtotal_vnd:>12,} {b.vat_vnd:>10,} "
                f"{b.grand_total_vnd:>13,} {b.n_estimated_intervals:>7}"
            )
    return 0


def cmd_quote(args: argparse.Namespace) -> int:
    """Quote a single bill for a given kWh — useful for what-if checks."""
    from evnmeter.tariff import compute_bill

    breakdown, subtotal, vat, grand = compute_bill(args.kwh)
    print(f"{'tier':<5} {'kwh':>5} {'rate':>10} {'cost':>14}")
    for b in breakdown:
        print(f"{b.tier:<5} {b.kwh:>5} {b.rate_vnd_per_kwh:>10,} {b.vnd:>14,}")
    print(f"{'subtotal':<22} {subtotal:>14,}")
    print(f"{'vat (8%)':<22} {vat:>14,}")
    print(f"{'grand total':<22} {grand:>14,}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from evnmeter.io_jsonl import load_intervals

    intervals = list(load_intervals(Path(args.input).read_text(encoding="utf-8")))
    by_meter: Counter[str] = Counter()
    estimated_by_meter: Counter[str] = Counter()
    for c in intervals:
        by_meter[c.meter_id] += c.kwh_x100
        if c.is_estimated:
            estimated_by_meter[c.meter_id] += 1
    payload = {
        "n_intervals": len(intervals),
        "n_meters": len(by_meter),
        "total_kwh": sum(by_meter.values()) // 100,
        "estimated_intervals": sum(estimated_by_meter.values()),
        "per_meter": {
            m: {
                "total_kwh": kwh // 100,
                "estimated_intervals": estimated_by_meter[m],
            }
            for m, kwh in sorted(by_meter.items())
        },
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="evnmeter",
        description="EVN smart-meter telemetry pipeline — derive, bill, detect anomalies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic meters + readings")
    sim.add_argument("--meters", type=int, default=20)
    sim.add_argument("--days", type=int, default=7)
    sim.add_argument("--gap-fraction", type=float, default=0.02)
    sim.add_argument("--out-of-order-fraction", type=float, default=0.05)
    sim.add_argument("--rollover-fraction", type=float, default=0.0)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    dr = sub.add_parser("derive", help="fold cumulative readings → per-interval kWh")
    dr.add_argument("--input", required=True, help="readings.jsonl")
    dr.add_argument("--output", default=None)
    dr.add_argument("--max-gap-minutes", type=int, default=90)
    dr.set_defaults(func=cmd_derive)

    an = sub.add_parser("anomaly", help="detect GAP / SPIKE / STUCK anomalies")
    an.add_argument("--input", required=True, help="intervals.jsonl")
    an.add_argument("--min-gap-minutes", type=int, default=120)
    an.add_argument("--spike-multiplier", type=float, default=5.0)
    an.add_argument("--stuck-intervals", type=int, default=12)
    an.add_argument("--show", type=int, default=5)
    an.set_defaults(func=cmd_anomaly)

    bl = sub.add_parser("bill", help="compute monthly bills from intervals")
    bl.add_argument("--input", required=True, help="intervals.jsonl")
    bl.add_argument("--period-start", required=True, help="ISO timestamp")
    bl.add_argument("--period-end", required=True, help="ISO timestamp")
    bl.add_argument("--output", default=None)
    bl.add_argument("--show", type=int, default=0)
    bl.set_defaults(func=cmd_bill)

    qt = sub.add_parser("quote", help="what-if tariff quote for one kWh value")
    qt.add_argument("kwh", type=int)
    qt.set_defaults(func=cmd_quote)

    sm = sub.add_parser("summary", help="JSON summary of an intervals file")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
