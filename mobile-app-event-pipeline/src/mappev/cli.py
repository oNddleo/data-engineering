"""``mappev`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from mappev import __version__

    print(f"mobile-app-event-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from mappev.io_jsonl import dump_events
    from mappev.simulator import generate

    events = generate(
        n_devices=args.devices,
        n_days=args.days,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_events(events), encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_events(events))
    return 0


def cmd_attribute(args: argparse.Namespace) -> int:
    from mappev.attribute import attribute
    from mappev.io_jsonl import dump_attributions, load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    attributions = attribute(
        events,
        click_window=timedelta(days=args.click_window_days),
        view_window=timedelta(hours=args.view_window_hours),
    )
    out_text = dump_attributions(attributions)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(attributions)} attributions to {args.output}", file=sys.stderr)
    if args.show:
        print(f"{'device':<14} {'source':<14} {'campaign':<24} {'lag_s':>8}")
        for a in attributions[: args.show]:
            print(
                f"{a.device_id:<14} {a.attributed_source:<14} "
                f"{a.attributed_campaign:<24} {a.attribution_lag_seconds:>8}"
            )
    return 0


def cmd_cohort(args: argparse.Namespace) -> int:
    from mappev.cohort import retention
    from mappev.io_jsonl import load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    cohorts = retention(events)
    print(f"{'date':<12} {'size':>6} {'D1%':>6} {'D7%':>6} {'D30%':>6}")
    for c in cohorts[: args.show]:
        print(
            f"{c.cohort_date:<12} {c.cohort_size:>6} "
            f"{c.d1_pct:>5.1f}% {c.d7_pct:>5.1f}% {c.d30_pct:>5.1f}%"
        )
    return 0


def cmd_ltv(args: argparse.Namespace) -> int:
    from mappev.cohort import ltv
    from mappev.io_jsonl import load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    rows = ltv(events)
    print(f"{'date':<12} {'size':>6} {'LTV_D1':>10} {'LTV_D7':>10} {'LTV_D30':>10}")
    for r in rows[: args.show]:
        print(
            f"{r.cohort_date:<12} {r.cohort_size:>6} "
            f"{r.ltv_d1_vnd:>10,} {r.ltv_d7_vnd:>10,} {r.ltv_d30_vnd:>10,}"
        )
    return 0


def cmd_fraud(args: argparse.Namespace) -> int:
    from mappev.attribute import attribute
    from mappev.fraud import find_click_injection, find_install_spam
    from mappev.io_jsonl import load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    attributions = attribute(events)
    injections = find_click_injection(
        attributions,
        min_lag_seconds=args.min_lag_seconds,
    )
    spam = find_install_spam(
        events,
        attributions,
        min_installs=args.min_installs,
        min_d1_rate_pct=args.min_d1_rate_pct,
    )
    print(f"CLICK_INJECTION ({len(injections)}):")
    for f in injections[: args.show]:
        print(f"  {f.source:<35} {f.detail}")
    print(f"INSTALL_SPAM ({len(spam)}):")
    for f in spam[: args.show]:
        print(f"  {f.source:<35} {f.detail}")
    return 0 if not (injections or spam) else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from mappev.attribute import attribute
    from mappev.cohort import ltv, retention
    from mappev.io_jsonl import load_events
    from mappev.schema import EventKind

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    by_kind: Counter[str] = Counter()
    for e in events:
        by_kind[e.kind.value] += 1
    attributions = attribute(events)
    by_source: Counter[str] = Counter()
    for a in attributions:
        by_source[a.attributed_source] += 1
    cohorts = retention(events)
    ltv_rows = ltv(events)
    total_revenue = sum(e.revenue_vnd for e in events if e.kind is EventKind.PURCHASE)
    payload = {
        "n_events": len(events),
        "n_devices_attributed": len(attributions),
        "events_by_kind": dict(sorted(by_kind.items())),
        "installs_by_source": dict(sorted(by_source.items())),
        "n_cohorts": len(cohorts),
        "total_purchase_revenue_vnd": total_revenue,
        "weighted_avg_d1_retention_pct": _weighted_avg(
            [(c.cohort_size, c.d1_pct) for c in cohorts]
        ),
        "weighted_avg_d30_ltv_vnd": _weighted_avg(
            [(c.cohort_size, float(c.ltv_d30_vnd)) for c in ltv_rows]
        ),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def _weighted_avg(pairs: list[tuple[int, float]]) -> float:
    """Compute a weighted average; returns 0.0 for empty input."""
    total_weight = sum(w for w, _ in pairs)
    if total_weight == 0:
        return 0.0
    return round(sum(w * v for w, v in pairs) / total_weight, 1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="mappev",
        description="Mobile-app event pipeline — attribution, cohort, LTV, fraud.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic event stream")
    sim.add_argument("--devices", type=int, default=200)
    sim.add_argument("--days", type=int, default=30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    at = sub.add_parser("attribute", help="last-touch attribution with windows")
    at.add_argument("--input", required=True)
    at.add_argument("--output", default=None)
    at.add_argument("--click-window-days", type=int, default=7)
    at.add_argument("--view-window-hours", type=int, default=24)
    at.add_argument("--show", type=int, default=10)
    at.set_defaults(func=cmd_attribute)

    co = sub.add_parser("cohort", help="install-day retention curves (D1/D7/D30)")
    co.add_argument("--input", required=True)
    co.add_argument("--show", type=int, default=10)
    co.set_defaults(func=cmd_cohort)

    lt = sub.add_parser("ltv", help="lifetime-value per install cohort")
    lt.add_argument("--input", required=True)
    lt.add_argument("--show", type=int, default=10)
    lt.set_defaults(func=cmd_ltv)

    fr = sub.add_parser("fraud", help="click-injection + install-spam detection")
    fr.add_argument("--input", required=True)
    fr.add_argument("--min-lag-seconds", type=int, default=20)
    fr.add_argument("--min-installs", type=int, default=5)
    fr.add_argument("--min-d1-rate-pct", type=int, default=5)
    fr.add_argument("--show", type=int, default=10)
    fr.set_defaults(func=cmd_fraud)

    sm = sub.add_parser("summary", help="JSON roll-up of events + cohorts + LTV")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
