"""``flashpipe`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from flashpipe import __version__

    print(f"flash-sale-event-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from flashpipe.io_jsonl import dump_events
    from flashpipe.simulator import generate

    events = generate(
        n_events=args.events,
        n_items=args.items,
        seed=args.seed,
        inject_stampede_item=args.stampede_item,
        out_of_order_fraction=args.disorder,
    )
    out = dump_events(events)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from flashpipe.engine import StreamEngine
    from flashpipe.io_jsonl import dump_aggregates, dump_hotness, load_events
    from flashpipe.sinks import InMemoryHotnessSink, InMemoryWindowSink

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    engine = StreamEngine(
        window_seconds=args.window,
        max_out_of_orderness_seconds=args.oo,
        hot_min_views=args.hot_views,
        hot_min_orders=args.hot_orders,
        stampede_multiplier=args.stampede_mul,
    )
    window_sink = InMemoryWindowSink()
    hot_sink = InMemoryHotnessSink()
    engine.consume_many(load_events(text), window_sink=window_sink, hotness_sink=hot_sink)
    snap = engine.snapshot()
    if args.output_windows:
        Path(args.output_windows).write_text(
            dump_aggregates(window_sink.received), encoding="utf-8"
        )
    if args.output_hotness:
        Path(args.output_hotness).write_text(dump_hotness(hot_sink.received), encoding="utf-8")
    sys.stdout.write(
        json.dumps(
            {
                "n_aggregates": window_sink.size,
                "n_hotness_events": hot_sink.size,
                "metrics": asdict(snap),
            },
            indent=2,
            default=str,
        )
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="flashpipe",
        description="Flash-sale event pipeline (watermark + tumbling windows + hotness detectors).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic flash-sale events as JSONL")
    sim.add_argument("--events", type=int, default=1000)
    sim.add_argument("--items", type=int, default=20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--stampede-item", dest="stampede_item", type=int, default=None)
    sim.add_argument("--disorder", type=float, default=0.0, help="fraction of late events")
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    rn = sub.add_parser("run", help="consume events + run windowed aggregations + emit hotness")
    rn.add_argument("--input", default=None)
    rn.add_argument("--window", type=int, default=1, help="tumbling window size in seconds")
    rn.add_argument("--oo", type=float, default=5.0, help="max out-of-orderness in seconds")
    rn.add_argument("--hot-views", dest="hot_views", type=int, default=1000)
    rn.add_argument("--hot-orders", dest="hot_orders", type=int, default=50)
    rn.add_argument("--stampede-mul", dest="stampede_mul", type=float, default=10.0)
    rn.add_argument("--output-windows", dest="output_windows", default=None)
    rn.add_argument("--output-hotness", dest="output_hotness", default=None)
    rn.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
