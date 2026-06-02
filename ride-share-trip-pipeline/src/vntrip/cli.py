"""``vntrip`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vntrip import __version__

    print(f"ride-share-trip-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vntrip.io_jsonl import dump_events
    from vntrip.simulator import generate

    events = generate(
        n_riders=args.riders,
        n_drivers=args.drivers,
        n_days=args.days,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_events(events), encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_events(events))
    return 0


def cmd_stitch(args: argparse.Namespace) -> int:
    from vntrip.io_jsonl import dump_trips, load_events
    from vntrip.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    trips = stitch(events)
    out_text = dump_trips(trips)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(trips)} trips to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'trip':<14} {'rider':<8} {'driver':<8} {'status':<10} " f"{'dist_m':>7} {'fare':>10}"
        )
        for t in trips[: args.show]:
            status = "DONE" if t.is_completed else ("CANCEL" if t.is_cancelled else "PENDING")
            print(
                f"{t.trip_id:<14} {t.rider_id:<8} "
                f"{(t.driver_id or '-'):<8} {status:<10} "
                f"{t.distance_m:>7} {t.fare_vnd:>10,}"
            )
    return 0


def cmd_fare(args: argparse.Namespace) -> int:
    from vntrip.fare import compute_fare
    from vntrip.io_jsonl import dump_fares, load_events
    from vntrip.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    trips = stitch(events)
    fares = [
        compute_fare(
            trip_id=t.trip_id,
            vehicle_class=t.vehicle_class,
            distance_m=t.distance_m,
            ride_seconds=t.ride_seconds,
            surge_bps=t.surge_bps,
        )
        for t in trips
        if t.is_completed and t.ride_seconds >= 0
    ]
    out_text = dump_fares(fares)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(fares)} fares to {args.output}", file=sys.stderr)
    if args.show:
        print(f"{'trip':<14} {'base':>8} {'dist':>8} {'time':>7} " f"{'surge×':>7} {'total':>10}")
        for f in fares[: args.show]:
            print(
                f"{f.trip_id:<14} {f.base_fare_vnd:>8,} "
                f"{f.distance_fare_vnd:>8,} {f.time_fare_vnd:>7,} "
                f"{f.surge_multiplier_bps / 10_000:>6.2f}× "
                f"{f.total_fare_vnd:>10,}"
            )
    return 0


def cmd_surge(args: argparse.Namespace) -> int:
    from vntrip.analytics import surge_windows
    from vntrip.io_jsonl import load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    windows = surge_windows(events)
    surging = [w for w in windows if w.is_surging]
    print(f"surge windows ({len(surging)}/{len(windows)}):")
    print(f"  {'district':<10} {'hour':<25} {'reqs':>5} {'done%':>6} {'surge×':>7}")
    for w in surging[: args.show]:
        print(
            f"  {w.district:<10} {w.hour_bucket:<25} {w.requests:>5} "
            f"{w.completion_rate_pct:>5.1f}% "
            f"{w.avg_surge_bps / 10_000:>6.2f}×"
        )
    return 0


def cmd_shifts(args: argparse.Namespace) -> int:
    from vntrip.analytics import driver_shifts
    from vntrip.io_jsonl import load_events
    from vntrip.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    shifts = driver_shifts(stitch(events))
    print(
        f"{'driver':<10} {'date':<12} {'trips':>6} " f"{'rev_vnd':>10} {'online_h':>9} {'util%':>6}"
    )
    for s in shifts[: args.show]:
        print(
            f"{s.driver_id:<10} {s.shift_date:<12} {s.trips_completed:>6} "
            f"{s.revenue_vnd:>10,} {s.online_seconds / 3600:>8.1f}h "
            f"{s.utilization_pct:>5.1f}%"
        )
    return 0


def cmd_fraud(args: argparse.Namespace) -> int:
    from vntrip.fraud import find_cancel_abuse, find_phantom_trips
    from vntrip.io_jsonl import load_events
    from vntrip.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    trips = stitch(events)
    abuse = find_cancel_abuse(
        trips,
        min_accepts=args.min_accepts,
        max_cancel_rate_pct=args.max_cancel_rate_pct,
        max_accept_to_cancel_seconds=args.max_lag_seconds,
    )
    phantom = find_phantom_trips(
        trips,
        min_distance_m=args.min_distance_m,
        min_ride_seconds=args.min_ride_seconds,
    )
    print(f"CANCEL_ABUSE ({len(abuse)}):")
    for f in abuse[: args.show]:
        print(f"  {f.subject_id:<10} {f.detail}")
    print(f"PHANTOM_TRIP ({len(phantom)}):")
    for f in phantom[: args.show]:
        print(f"  {f.subject_id:<10} {f.detail}")
    return 0 if not (abuse or phantom) else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from vntrip.analytics import driver_shifts, surge_windows
    from vntrip.io_jsonl import load_events
    from vntrip.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    trips = stitch(events)
    by_kind: Counter[str] = Counter()
    for e in events:
        by_kind[e.kind.value] += 1
    completed = sum(1 for t in trips if t.is_completed)
    cancelled = sum(1 for t in trips if t.is_cancelled)
    total_revenue = sum(t.fare_vnd for t in trips if t.is_completed)
    shifts = driver_shifts(trips)
    surges = surge_windows(events)
    surging = [w for w in surges if w.is_surging]
    payload = {
        "n_events": len(events),
        "n_trips": len(trips),
        "n_completed": completed,
        "n_cancelled": cancelled,
        "completion_rate_pct": round(completed / len(trips) * 100, 1) if trips else 0.0,
        "events_by_kind": dict(sorted(by_kind.items())),
        "total_revenue_vnd": total_revenue,
        "n_driver_shifts": len(shifts),
        "n_surge_windows_active": len(surging),
        "avg_driver_utilization_pct": round(
            sum(s.utilization_pct for s in shifts) / len(shifts),
            1,
        )
        if shifts
        else 0.0,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vntrip",
        description="Grab/Gojek/Be-style ride-hailing trip pipeline.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic trip-event stream")
    sim.add_argument("--riders", type=int, default=100)
    sim.add_argument("--drivers", type=int, default=30)
    sim.add_argument("--days", type=int, default=7)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    st = sub.add_parser("stitch", help="stitch event stream into Trip rows")
    st.add_argument("--input", required=True)
    st.add_argument("--output", default=None)
    st.add_argument("--show", type=int, default=10)
    st.set_defaults(func=cmd_stitch)

    fa = sub.add_parser("fare", help="compute fare breakdown per completed trip")
    fa.add_argument("--input", required=True)
    fa.add_argument("--output", default=None)
    fa.add_argument("--show", type=int, default=10)
    fa.set_defaults(func=cmd_fare)

    sg = sub.add_parser("surge", help="detect district × hour surge windows")
    sg.add_argument("--input", required=True)
    sg.add_argument("--show", type=int, default=10)
    sg.set_defaults(func=cmd_surge)

    dr = sub.add_parser("shifts", help="per-driver daily utilization shifts")
    dr.add_argument("--input", required=True)
    dr.add_argument("--show", type=int, default=10)
    dr.set_defaults(func=cmd_shifts)

    fr = sub.add_parser("fraud", help="cancel-abuse + phantom-trip detection")
    fr.add_argument("--input", required=True)
    fr.add_argument("--min-accepts", type=int, default=10)
    fr.add_argument("--max-cancel-rate-pct", type=int, default=30)
    fr.add_argument("--max-lag-seconds", type=int, default=30)
    fr.add_argument("--min-distance-m", type=int, default=200)
    fr.add_argument("--min-ride-seconds", type=int, default=30)
    fr.add_argument("--show", type=int, default=10)
    fr.set_defaults(func=cmd_fraud)

    sm = sub.add_parser("summary", help="JSON roll-up of events + trips + shifts")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
