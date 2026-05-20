"""``windows`` CLI — simulate, aggregate (tumbling/sliding/session)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from windows import __version__

    print(f"time-window-aggregator {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from windows.io_jsonl import dump_events
    from windows.simulator import bursty_stream, uniform_stream

    if args.bursty:
        events = bursty_stream(
            n_keys=args.keys,
            n_bursts=args.bursts,
            events_per_burst=args.burst_size,
            seed=args.seed,
        )
    else:
        events = uniform_stream(
            n_keys=args.keys,
            n_events_per_key=args.events,
            interval_ms=args.interval_ms,
            seed=args.seed,
        )
    if args.output:
        Path(args.output).write_text(dump_events(events), encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_events(events))
    return 0


def cmd_tumbling(args: argparse.Namespace) -> int:
    from windows.io_jsonl import dump_aggs, load_events
    from windows.tumbling import aggregate

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    aggs = aggregate(events, width_ms=args.width_ms)
    if args.output:
        Path(args.output).write_text(dump_aggs(aggs), encoding="utf-8")
        print(f"wrote {len(aggs)} aggregates to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_aggs(aggs))
    return 0


def cmd_sliding(args: argparse.Namespace) -> int:
    from windows.io_jsonl import dump_aggs, load_events
    from windows.sliding import aggregate

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    aggs = aggregate(events, width_ms=args.width_ms, stride_ms=args.stride_ms)
    if args.output:
        Path(args.output).write_text(dump_aggs(aggs), encoding="utf-8")
        print(f"wrote {len(aggs)} aggregates to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_aggs(aggs))
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    from windows.io_jsonl import dump_aggs, load_events
    from windows.session import aggregate

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    aggs = aggregate(events, timeout_ms=args.timeout_ms)
    if args.output:
        Path(args.output).write_text(dump_aggs(aggs), encoding="utf-8")
        print(f"wrote {len(aggs)} sessions to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_aggs(aggs))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """JSON summary of an aggregate stream."""
    from windows.io_jsonl import load_aggs

    aggs = load_aggs(Path(args.input).read_text(encoding="utf-8"))
    payload = {
        "n_aggregates": len(aggs),
        "n_distinct_keys": len({a.key for a in aggs}),
        "total_count": sum(a.count for a in aggs),
        "total_sum": sum(a.sum_value for a in aggs),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="windows",
        description="Streaming time-window aggregator — tumbling / sliding / session.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic event stream")
    sim.add_argument("--keys", type=int, default=5)
    sim.add_argument("--events", type=int, default=100)
    sim.add_argument("--interval-ms", type=int, default=1_000)
    sim.add_argument("--bursty", action="store_true")
    sim.add_argument("--bursts", type=int, default=5)
    sim.add_argument("--burst-size", type=int, default=20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    tb = sub.add_parser("tumbling", help="tumbling-window aggregation")
    tb.add_argument("--input", required=True)
    tb.add_argument("--width-ms", type=int, required=True)
    tb.add_argument("--output", default=None)
    tb.set_defaults(func=cmd_tumbling)

    sl = sub.add_parser("sliding", help="sliding-window aggregation")
    sl.add_argument("--input", required=True)
    sl.add_argument("--width-ms", type=int, required=True)
    sl.add_argument("--stride-ms", type=int, required=True)
    sl.add_argument("--output", default=None)
    sl.set_defaults(func=cmd_sliding)

    se = sub.add_parser("session", help="session-window aggregation")
    se.add_argument("--input", required=True)
    se.add_argument("--timeout-ms", type=int, required=True)
    se.add_argument("--output", default=None)
    se.set_defaults(func=cmd_session)

    sm = sub.add_parser("summary", help="summary stats of an aggregate file")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
