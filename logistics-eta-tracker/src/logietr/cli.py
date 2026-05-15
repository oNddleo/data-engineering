"""``logietr`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from logietr import __version__

    print(f"logistics-eta-tracker {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from logietr.io_jsonl import dump_events, dump_shipments
    from logietr.simulator import generate

    shipments, events = generate(
        n_shipments=args.n,
        failure_rate=args.failure_rate,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "shipments.jsonl").write_text(dump_shipments(shipments), encoding="utf-8")
    (out_dir / "events.jsonl").write_text(dump_events(events), encoding="utf-8")
    print(
        f"wrote {len(shipments)} shipments + {len(events)} events to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def _load_statuses(in_dir: Path):  # type: ignore[no-untyped-def]
    """Load + fold sources → ``dict[shipment_id, ShipmentStatus]``."""
    from logietr.io_jsonl import load_events, load_shipments
    from logietr.tracker import apply_events

    shipments = list(load_shipments((in_dir / "shipments.jsonl").read_text(encoding="utf-8")))
    events = list(load_events((in_dir / "events.jsonl").read_text(encoding="utf-8")))
    return shipments, apply_events(shipments, events)


def cmd_status(args: argparse.Namespace) -> int:
    from logietr.tracker import state_distribution

    _, statuses = _load_statuses(Path(args.in_dir))
    dist = state_distribution(statuses)
    print(f"{'state':<20} {'count':>8}")
    for state, count in dist.items():
        print(f"{state.value:<20} {count:>8}")
    return 0


def cmd_eta(args: argparse.Namespace) -> int:
    from logietr.eta import build_lane_stats, predict_eta
    from logietr.schema import ShipmentState

    _, statuses = _load_statuses(Path(args.in_dir))
    completed = [s for s in statuses.values() if s.state is ShipmentState.DELIVERED]
    pending = [s for s in statuses.values() if not s.is_terminal]
    lanes = build_lane_stats(completed, min_samples=args.min_samples)
    predictions = predict_eta(pending, lanes)
    print(f"{'shipment':<10} {'src':<18} {'p50_at':<25} {'p90_at':<25} {'band_h':>7}")
    for p in predictions[: args.n]:
        print(
            f"{p.shipment_id:<10} {p.source:<18} "
            f"{p.predicted_p50.isoformat():<25} {p.predicted_p90.isoformat():<25} "
            f"{p.confidence_band_seconds / 3600:>6.1f}h"
        )
    return 0


def cmd_breaches(args: argparse.Namespace) -> int:
    from logietr.sla import find_overdue, find_stuck

    _, statuses = _load_statuses(Path(args.in_dir))
    now = (
        datetime.fromisoformat(args.now)
        if args.now
        else max((s.last_event_at for s in statuses.values()), default=datetime.now().astimezone())
    )
    overdue = find_overdue(statuses, now)
    stuck = find_stuck(statuses, now, stuck_after=timedelta(hours=args.stuck_hours))
    print(f"OVERDUE ({len(overdue)}):")
    for b in overdue[: args.n]:
        print(f"  {b.shipment_id:<10} {b.state.value:<18} overdue {b.overdue_hours:.1f}h")
    print(f"STUCK ({len(stuck)}):")
    for b in stuck[: args.n]:
        print(f"  {b.shipment_id:<10} {b.state.value:<18} stuck   {b.overdue_hours:.1f}h")
    return 0


def cmd_carriers(args: argparse.Namespace) -> int:
    from logietr.leaderboard import carrier_scorecards, rank_by_on_time

    _, statuses = _load_statuses(Path(args.in_dir))
    cards = carrier_scorecards(list(statuses.values()))
    ranked = rank_by_on_time(cards, min_volume=args.min_volume)
    print(
        f"{'carrier':<8} {'total':>6} {'deliv':>6} {'fail':>5} {'ret':>4} {'on_time%':>9} {'median_h':>9}"
    )
    for c in ranked:
        print(
            f"{c.carrier.value:<8} {c.n_total:>6} {c.n_delivered:>6} "
            f"{c.n_failed:>5} {c.n_returned:>4} "
            f"{c.on_time_pct:>8.1f}% {c.median_transit_hours:>8.1f}h"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from logietr.schema import ShipmentState
    from logietr.tracker import state_distribution

    _, statuses = _load_statuses(Path(args.in_dir))
    dist = state_distribution(statuses)
    payload = {
        "n_shipments": len(statuses),
        "by_state": {s.value: dist[s] for s in ShipmentState},
        "n_dropped_events": sum(s.n_dropped_events for s in statuses.values()),
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="logietr",
        description="VN logistics ETA + SLA tracker (GHN, GHTK, Viettel Post, VN Post).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic shipments + tracking events")
    sim.add_argument("--n", type=int, default=300)
    sim.add_argument("--failure-rate", type=float, default=0.05)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    st = sub.add_parser("status", help="state distribution across all shipments")
    st.add_argument("--in-dir", required=True)
    st.set_defaults(func=cmd_status)

    et = sub.add_parser("eta", help="predict ETA for pending shipments")
    et.add_argument("--in-dir", required=True)
    et.add_argument("--min-samples", type=int, default=3)
    et.add_argument("--n", type=int, default=20)
    et.set_defaults(func=cmd_eta)

    br = sub.add_parser("breaches", help="list OVERDUE and STUCK shipments")
    br.add_argument("--in-dir", required=True)
    br.add_argument("--now", default=None, help="ISO timestamp; defaults to last event time")
    br.add_argument("--stuck-hours", type=int, default=24)
    br.add_argument("--n", type=int, default=20)
    br.set_defaults(func=cmd_breaches)

    cr = sub.add_parser("carriers", help="carrier leaderboard")
    cr.add_argument("--in-dir", required=True)
    cr.add_argument("--min-volume", type=int, default=10)
    cr.set_defaults(func=cmd_carriers)

    sm = sub.add_parser("summary", help="JSON summary of state distribution")
    sm.add_argument("--in-dir", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
