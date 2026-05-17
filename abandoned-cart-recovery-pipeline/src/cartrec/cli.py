"""``cartrec`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from cartrec import __version__

    print(f"abandoned-cart-recovery-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from cartrec.io_jsonl import dump_events
    from cartrec.simulator import generate

    events = generate(
        n_buyers=args.buyers,
        recovery_fraction=args.recovery_fraction,
        seed=args.seed,
    )
    out_text = dump_events(events)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(
            f"wrote {len(events)} events to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_sessionize(args: argparse.Namespace) -> int:
    from cartrec.io_jsonl import dump_sessions, load_events
    from cartrec.sessionize import sessionize

    events = list(load_events(Path(args.input).read_text(encoding="utf-8")))
    sessions = sessionize(events, idle_gap_minutes=args.idle_gap_minutes)
    out_text = dump_sessions(sessions)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(
            f"wrote {len(sessions)} sessions to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    from cartrec.detect import abandon_rate, find_abandoned
    from cartrec.io_jsonl import load_sessions

    sessions = list(load_sessions(Path(args.input).read_text(encoding="utf-8")))
    abandoned = find_abandoned(sessions, min_cart_vnd=args.min_cart_vnd)
    rate = abandon_rate(sessions)
    print(f"{'session':<60} {'reason':<18} {'cart_vnd':>10}")
    for ab in abandoned[: args.show]:
        print(f"{ab.session_id:<60} {ab.reason.value:<18} " f"{ab.session.cart_value_vnd:>10,}")
    print(
        f"\nAbandon rate: {rate * 100:.1f}% "
        f"({len(abandoned)}/{sum(1 for s in sessions if s.n_add > 0)} carting sessions)"
    )
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    from cartrec.campaign import schedule
    from cartrec.detect import find_abandoned
    from cartrec.io_jsonl import dump_touches, load_sessions

    sessions = list(load_sessions(Path(args.input).read_text(encoding="utf-8")))
    abandoned = find_abandoned(sessions, min_cart_vnd=args.min_cart_vnd)
    touches = schedule(abandoned)
    out_text = dump_touches(touches)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(
            f"wrote {len(touches)} touches across {len(abandoned)} abandoned sessions to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_attribute(args: argparse.Namespace) -> int:
    from cartrec.attribute import attribute, conversion_by_channel, conversion_rate
    from cartrec.io_jsonl import dump_attributed, load_events, load_touches

    touches = list(load_touches(Path(args.touches).read_text(encoding="utf-8")))
    events = list(load_events(Path(args.events).read_text(encoding="utf-8")))
    attributed = attribute(
        touches,
        events,
        attribution_window_hours=args.window_hours,
        last_touch=args.last_touch,
    )
    out_text = dump_attributed(attributed)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
    rate = conversion_rate(attributed)
    print(
        f"Conversion rate: {rate * 100:.2f}% ({sum(1 for a in attributed if a.verdict.value == 'CONVERTED')}/{len(attributed)})"
    )
    by_channel = conversion_by_channel(attributed)
    for ch, r in by_channel.items():
        print(f"  {ch:<6} {r * 100:.2f}%")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from cartrec.detect import find_abandoned
    from cartrec.io_jsonl import load_sessions

    sessions = list(load_sessions(Path(args.input).read_text(encoding="utf-8")))
    abandoned = find_abandoned(sessions, min_cart_vnd=args.min_cart_vnd)
    reason_counts: Counter[str] = Counter()
    for ab in abandoned:
        reason_counts[ab.reason.value] += 1
    payload = {
        "n_sessions": len(sessions),
        "n_carting_sessions": sum(1 for s in sessions if s.n_add > 0),
        "n_completed": sum(1 for s in sessions if s.completed_checkout),
        "n_abandoned": len(abandoned),
        "by_reason": dict(reason_counts),
        "total_recoverable_vnd": sum(ab.session.cart_value_vnd for ab in abandoned),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cartrec",
        description="Abandoned-cart recovery pipeline — sessionize, detect, schedule, attribute.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="generate synthetic event stream")
    sim.add_argument("--buyers", type=int, default=200)
    sim.add_argument("--recovery-fraction", type=float, default=0.10)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ss = sub.add_parser("sessionize", help="fold events into sessions")
    ss.add_argument("--input", required=True, help="events.jsonl")
    ss.add_argument("--idle-gap-minutes", type=int, default=30)
    ss.add_argument("--output", default=None)
    ss.set_defaults(func=cmd_sessionize)

    dt = sub.add_parser("detect", help="find abandoned sessions")
    dt.add_argument("--input", required=True, help="sessions.jsonl")
    dt.add_argument("--min-cart-vnd", type=int, default=50_000)
    dt.add_argument("--show", type=int, default=10)
    dt.set_defaults(func=cmd_detect)

    sc = sub.add_parser("schedule", help="schedule recovery touches")
    sc.add_argument("--input", required=True, help="sessions.jsonl")
    sc.add_argument("--min-cart-vnd", type=int, default=50_000)
    sc.add_argument("--output", default=None)
    sc.set_defaults(func=cmd_schedule)

    at = sub.add_parser("attribute", help="attribute conversions to touches")
    at.add_argument("--touches", required=True)
    at.add_argument("--events", required=True)
    at.add_argument("--window-hours", type=int, default=24)
    at.add_argument(
        "--last-touch",
        action="store_true",
        help="use last-touch attribution instead of first-touch",
    )
    at.add_argument("--output", default=None)
    at.set_defaults(func=cmd_attribute)

    sm = sub.add_parser("summary", help="JSON summary of sessions / abandons")
    sm.add_argument("--input", required=True)
    sm.add_argument("--min-cart-vnd", type=int, default=50_000)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
