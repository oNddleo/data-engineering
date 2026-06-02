"""``vnpost`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnpost import __version__

    print(f"vnpost-tracking-event-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnpost.io_jsonl import dump_events
    from vnpost.simulator import generate

    events = generate(
        n_parcels=args.parcels,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_events(events), encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_events(events))
    return 0


def cmd_stitch(args: argparse.Namespace) -> int:
    from vnpost.io_jsonl import dump_parcels, load_events
    from vnpost.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    parcels = stitch(events)
    out_text = dump_parcels(parcels)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(parcels)} parcels to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'tracking':<14} {'courier':<5} {'status':<10} "
            f"{'origin':<10} {'dest':<10} {'evts':>4}"
        )
        for p in parcels[: args.show]:
            print(
                f"{p.tracking_id:<14} {p.courier.value:<5} "
                f"{p.status.value:<10} {p.origin_hub or '-':<10} "
                f"{p.dest_hub or '-':<10} {p.n_events:>4}"
            )
    return 0


def cmd_sla(args: argparse.Namespace) -> int:
    from vnpost.io_jsonl import load_events
    from vnpost.sla import compute_sla
    from vnpost.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    parcels = stitch(events)
    slas = compute_sla(parcels, tet_aware=not args.no_tet_aware)
    print(
        f"{'courier':<5} {'parcels':>8} {'delivered':>10} "
        f"{'on-time%':>9} {'p95_h':>6} {'med_h':>6}"
    )
    for s in slas:
        print(
            f"{s.courier.value:<5} {s.n_parcels:>8} {s.n_delivered:>10} "
            f"{s.on_time_rate_pct:>8.1f}% "
            f"{s.p95_transit_hours:>5}h {s.median_transit_hours:>5}h"
        )
    return 0


def cmd_fraud(args: argparse.Namespace) -> int:
    from vnpost.fraud import find_abnormal_dwell, find_scan_skipping
    from vnpost.io_jsonl import load_events
    from vnpost.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    parcels = stitch(events)
    scan_skip = find_scan_skipping(parcels)
    abnormal = find_abnormal_dwell(events)
    print(f"SCAN_SKIPPING ({len(scan_skip)}):")
    for f in scan_skip[: args.show]:
        print(f"  {f.courier.value} {f.tracking_id:<14} {f.detail}")
    print(f"ABNORMAL_DWELL ({len(abnormal)}):")
    for f in abnormal[: args.show]:
        print(f"  {f.courier.value} {f.tracking_id:<14} {f.detail}")
    return 0 if not (scan_skip or abnormal) else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from vnpost.fraud import find_abnormal_dwell, find_scan_skipping
    from vnpost.io_jsonl import load_events
    from vnpost.sla import compute_sla
    from vnpost.state import stitch

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    parcels = stitch(events)
    slas = compute_sla(parcels)
    by_status: Counter[str] = Counter()
    for p in parcels:
        by_status[p.status.value] += 1
    by_courier: Counter[str] = Counter()
    for p in parcels:
        by_courier[p.courier.value] += 1
    scan_skip = find_scan_skipping(parcels)
    abnormal = find_abnormal_dwell(events)
    avg_on_time = sum(s.on_time_rate_pct for s in slas) / len(slas) if slas else 0.0
    payload = {
        "n_events": len(events),
        "n_parcels": len(parcels),
        "by_status": dict(sorted(by_status.items())),
        "by_courier": dict(sorted(by_courier.items())),
        "avg_on_time_rate_pct": round(avg_on_time, 1),
        "n_scan_skip_findings": len(scan_skip),
        "n_abnormal_dwell_findings": len(abnormal),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnpost",
        description="VN courier tracking event pipeline.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic tracking event stream")
    sim.add_argument("--parcels", type=int, default=200)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    st = sub.add_parser("stitch", help="stitch events into Parcel rows")
    st.add_argument("--input", required=True)
    st.add_argument("--output", default=None)
    st.add_argument("--show", type=int, default=10)
    st.set_defaults(func=cmd_stitch)

    sla = sub.add_parser("sla", help="per-courier on-time SLA roll-up")
    sla.add_argument("--input", required=True)
    sla.add_argument(
        "--no-tet-aware", action="store_true", help="don't subtract Tết block from transit time"
    )
    sla.set_defaults(func=cmd_sla)

    fr = sub.add_parser("fraud", help="scan-skipping + abnormal-dwell detection")
    fr.add_argument("--input", required=True)
    fr.add_argument("--show", type=int, default=10)
    fr.set_defaults(func=cmd_fraud)

    sm = sub.add_parser("summary", help="JSON roll-up of all signals")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
