"""``vnride`` CLI — operators, pricing, simulate, settle, fraud."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnride import __version__

    print(f"vn-ride-hailing-trip-pipeline {__version__}")
    return 0


def cmd_operators(_args: argparse.Namespace) -> int:
    """List bundled VN ride-hailing operators."""
    from vnride.operators import all_operators

    print(f"{'ABBR':<8} {'NAME':<45} {'CAR%':>5} {'BIKE%':>6} {'SHARE%':>7}")
    for op in all_operators():
        print(
            f"{op.abbreviation:<8} {op.name_en[:45]:<45} "
            f"{op.commission_car_bps / 100:>5.1f} "
            f"{op.commission_bike_bps / 100:>6.1f} "
            f"{op.market_share_pct:>6.1f}%",
        )
    return 0


def cmd_cities(_args: argparse.Namespace) -> int:
    """List bundled VN cities."""
    from vnride.operators import all_cities

    print(f"{'CODE':<5} {'NAME':<25} {'POP(k)':>8} {'PEAK_SURGE':>11}")
    for c in all_cities():
        print(
            f"{c.code:<5} {c.name_en[:25]:<25} "
            f"{c.population_thousands:>8,} "
            f"{c.base_surge_during_peak_bps / 10_000:>10.2f}x",
        )
    return 0


def cmd_quote(args: argparse.Namespace) -> int:
    """Quote a fare for a hypothetical trip."""
    from vnride.pricing import quote
    from vnride.schema import ServiceType

    service = ServiceType(args.service.upper())
    fare = quote(
        service=service,
        distance_cm=int(args.km * 100_000),
        duration_seconds=args.minutes * 60,
        surge_bps=args.surge_bps,
    )
    payload = {
        "service": service.value,
        "distance_km": args.km,
        "duration_min": args.minutes,
        "surge_multiplier": fare.surge_multiplier,
        "base_vnd": fare.base_vnd,
        "distance_vnd": fare.distance_vnd,
        "duration_vnd": fare.duration_vnd,
        "booking_vnd": fare.booking_vnd,
        "total_vnd": fare.total_vnd,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnride.io_jsonl import dump_trips
    from vnride.simulator import generate

    trips = generate(
        n_riders=args.riders,
        n_drivers=args.drivers,
        n_days=args.days,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_trips(trips), encoding="utf-8")
        print(f"wrote {len(trips)} trips to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_trips(trips))
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    from vnride.io_jsonl import dump_settlements, load_trips
    from vnride.settlement import aggregate_daily

    trips = load_trips(Path(args.input).read_text(encoding="utf-8"))
    settlements = aggregate_daily(trips)
    if args.output:
        Path(args.output).write_text(
            dump_settlements(settlements),
            encoding="utf-8",
        )
        print(
            f"wrote {len(settlements)} settlements to {args.output}",
            file=sys.stderr,
        )
    if args.show:
        print(
            f"{'date':<12} {'driver':<10} {'op':<8} {'#comp':>6} "
            f"{'gross':>12} {'commission':>12} {'net':>12}",
        )
        for s in settlements[: args.show]:
            print(
                f"{s.date:<12} {s.driver_id:<10} {s.operator:<8} "
                f"{s.n_completed_trips:>6} {s.gross_revenue_vnd:>12,} "
                f"{s.commission_vnd:>12,} {s.net_payable_vnd:>12,}",
            )
    return 0


def cmd_fraud(args: argparse.Namespace) -> int:
    from vnride.fraud import (
        find_cancellation_abuse,
        find_ghost_rides,
        find_surge_gaming,
    )
    from vnride.io_jsonl import load_trips

    trips = load_trips(Path(args.input).read_text(encoding="utf-8"))
    ghost = find_ghost_rides(trips)
    cancel_abuse = find_cancellation_abuse(trips)
    surge = find_surge_gaming(trips)

    print(f"GHOST_RIDE ({len(ghost)}):")
    for f in ghost[: args.show]:
        print(f"  {f.subject_id:<16} {f.operator:<8} {f.detail}")
    print(f"CANCELLATION_ABUSE ({len(cancel_abuse)}):")
    for f in cancel_abuse[: args.show]:
        print(f"  {f.subject_id:<16} {f.operator:<8} {f.detail}")
    print(f"SURGE_GAMING ({len(surge)}):")
    for f in surge[: args.show]:
        print(f"  {f.subject_id:<32} {f.operator:<8} {f.detail}")
    return 0 if not (ghost or cancel_abuse or surge) else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from vnride.io_jsonl import load_trips
    from vnride.schema import TripState

    trips = load_trips(Path(args.input).read_text(encoding="utf-8"))
    by_state: Counter[str] = Counter()
    by_operator: Counter[str] = Counter()
    by_service: Counter[str] = Counter()
    total_revenue = 0
    for t in trips:
        by_state[t.state.value] += 1
        by_operator[t.operator] += 1
        by_service[t.service.value] += 1
        if t.fare is not None and t.state is TripState.COMPLETED:
            total_revenue += t.fare.total_vnd
    payload = {
        "n_trips": len(trips),
        "n_riders": len({t.rider_id for t in trips}),
        "n_drivers": len({t.driver_id for t in trips if t.driver_id}),
        "trips_by_state": dict(sorted(by_state.items())),
        "trips_by_operator": dict(sorted(by_operator.items())),
        "trips_by_service": dict(sorted(by_service.items())),
        "completed_revenue_vnd": total_revenue,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnride",
        description="VN ride-hailing trip pipeline — pricing, settlement, fraud.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("operators").set_defaults(func=cmd_operators)
    sub.add_parser("cities").set_defaults(func=cmd_cities)

    qt = sub.add_parser("quote", help="quote a fare for a hypothetical trip")
    qt.add_argument("--service", default="CAR")
    qt.add_argument("--km", type=float, default=5.0)
    qt.add_argument("--minutes", type=int, default=15)
    qt.add_argument("--surge-bps", type=int, default=10_000)
    qt.set_defaults(func=cmd_quote)

    sim = sub.add_parser("simulate", help="emit a synthetic trip stream")
    sim.add_argument("--riders", type=int, default=50)
    sim.add_argument("--drivers", type=int, default=20)
    sim.add_argument("--days", type=int, default=30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    st = sub.add_parser("settle", help="daily driver settlement rollup")
    st.add_argument("--input", required=True)
    st.add_argument("--output", default=None)
    st.add_argument("--show", type=int, default=10)
    st.set_defaults(func=cmd_settle)

    fr = sub.add_parser("fraud", help="detect ghost / cancel / surge fraud")
    fr.add_argument("--input", required=True)
    fr.add_argument("--show", type=int, default=5)
    fr.set_defaults(func=cmd_fraud)

    sm = sub.add_parser("summary", help="JSON roll-up of pipeline run")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
