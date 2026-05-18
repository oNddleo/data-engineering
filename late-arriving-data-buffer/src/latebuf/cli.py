"""``latebuf`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from latebuf import __version__

    print(f"late-arriving-data-buffer {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from latebuf.io_jsonl import dump_events
    from latebuf.simulator import LatenessDistribution, generate

    events = generate(
        n_events=args.events,
        interval_seconds=args.interval,
        distribution=LatenessDistribution(args.distribution),
        max_lateness_seconds=args.max_lateness,
        p95_seconds=args.p95,
        punctuation_every=args.punctuation_every,
        seed=args.seed,
    )
    text = dump_events(events)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from latebuf.buffer import LateArrivingBuffer
    from latebuf.io_jsonl import dump_emitted, load_events
    from latebuf.metrics import compute_stats
    from latebuf.schema import BufferConfig, EmittedRecord, WatermarkStrategy

    config = BufferConfig(
        strategy=WatermarkStrategy(args.strategy),
        allowed_lateness=timedelta(seconds=args.allowed_lateness),
        periodic_tick=timedelta(seconds=args.tick),
    )
    buffer = LateArrivingBuffer(config=config)
    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    emitted: list[EmittedRecord] = []
    for e in events:
        emitted.extend(buffer.accept(e))
    emitted.extend(buffer.flush())
    if args.output:
        Path(args.output).write_text(dump_emitted(emitted), encoding="utf-8")
        print(f"wrote {len(emitted)} dispositions to {args.output}", file=sys.stderr)
    stats = compute_stats(buffer)
    if args.show:
        print(f"strategy:         {config.strategy.value}")
        print(f"allowed_lateness: {config.allowed_lateness.total_seconds():.0f}s")
        print(f"n_accepted:       {stats.n_accepted}")
        print(f"n_emitted:        {stats.n_emitted}")
        print(f"n_dead_lettered:  {stats.n_dead_lettered}")
        print(f"n_still_buffered: {stats.n_still_buffered}")
        print(f"drop_rate:        {stats.drop_rate_pct:.1f}%")
        print(f"max_lateness:     {stats.max_lateness_seconds}s")
        print(f"median_lateness:  {stats.median_lateness_seconds}s")
        print(f"p99_lateness:     {stats.p99_lateness_seconds}s")
    return 0 if stats.n_dead_lettered == 0 else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from latebuf.buffer import LateArrivingBuffer
    from latebuf.io_jsonl import load_events, stats_to_dict
    from latebuf.metrics import compute_stats
    from latebuf.schema import BufferConfig, WatermarkStrategy

    config = BufferConfig(
        strategy=WatermarkStrategy(args.strategy),
        allowed_lateness=timedelta(seconds=args.allowed_lateness),
        periodic_tick=timedelta(seconds=args.tick),
    )
    buffer = LateArrivingBuffer(config=config)
    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    for e in events:
        buffer.accept(e)
    buffer.flush()
    payload = stats_to_dict(compute_stats(buffer))
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="latebuf",
        description="Late-arriving event buffer with three watermark strategies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic event stream")
    sim.add_argument("--events", type=int, default=500)
    sim.add_argument(
        "--interval", type=float, default=1.0, help="seconds between consecutive ingest_times"
    )
    sim.add_argument("--distribution", choices=("BOUNDED", "HEAVY_TAIL"), default="BOUNDED")
    sim.add_argument("--max-lateness", type=int, default=30)
    sim.add_argument("--p95", type=int, default=5)
    sim.add_argument("--punctuation-every", type=int, default=100)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    run = sub.add_parser("run", help="run buffer over an event stream")
    run.add_argument("--input", required=True)
    run.add_argument("--output", default=None, help="JSONL output of EmittedRecords")
    run.add_argument(
        "--strategy", choices=("HEURISTIC", "PERIODIC", "PUNCTUATED"), default="HEURISTIC"
    )
    run.add_argument(
        "--allowed-lateness",
        type=int,
        default=10,
        help="watermark trails max(event_time) by this many seconds",
    )
    run.add_argument("--tick", type=int, default=5, help="PERIODIC tick interval (seconds)")
    run.add_argument("--show", action="store_true", help="print stats summary to stdout")
    run.set_defaults(func=cmd_run)

    sm = sub.add_parser("summary", help="JSON stats roll-up")
    sm.add_argument("--input", required=True)
    sm.add_argument(
        "--strategy", choices=("HEURISTIC", "PERIODIC", "PUNCTUATED"), default="HEURISTIC"
    )
    sm.add_argument("--allowed-lateness", type=int, default=10)
    sm.add_argument("--tick", type=int, default=5)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
