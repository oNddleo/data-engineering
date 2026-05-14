"""``n247mon`` command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _read_blacklist(path: str | None) -> set[str]:
    if not path:
        return set()
    out: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def cmd_info(_args: argparse.Namespace) -> int:
    from n247mon import __version__

    print(f"napas-247-transaction-monitor {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from n247mon.io_jsonl import dump_txns
    from n247mon.simulator import generate

    bl = list(_read_blacklist(args.blacklist))
    anomalies = [a.strip() for a in (args.inject or "").split(",") if a.strip()]
    txns = generate(
        n_txns=args.txns,
        seed=args.seed,
        inject_anomalies=anomalies,
        blacklist=bl,
    )
    output = dump_txns(txns)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"wrote {len(txns)} transactions to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    from n247mon.engine import MonitorEngine
    from n247mon.io_jsonl import dump_alerts, load_txns
    from n247mon.rules import BiometricRule, BlacklistRule, StructuringRule, VelocityRule

    text = (
        sys.stdin.read()
        if args.input == "-" or args.input is None
        else Path(args.input).read_text(encoding="utf-8")
    )
    bl = _read_blacklist(args.blacklist)
    engine = MonitorEngine(
        rules=[
            BiometricRule(),
            VelocityRule(window_seconds=args.velocity_window, threshold=args.velocity_threshold),
            StructuringRule(),
            BlacklistRule(bl),
        ]
    )
    alerts = engine.consume_many(load_txns(text))
    out_text = dump_alerts(alerts)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
    else:
        sys.stdout.write(out_text)
    if args.summary:
        s = engine.stats
        sys.stderr.write(
            f"\nSummary: {s.txns_seen} txns -> {s.alerts_fired} alerts\n"
            f"  by kind:     {dict((k.value, v) for k, v in s.alerts_by_kind.items())}\n"
            f"  by severity: {dict((k.value, v) for k, v in s.alerts_by_severity.items())}\n"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="n247mon",
        description="NAPAS 247 instant-transfer anomaly monitor with Decision 2345 biometric rules.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic NAPAS 247 traffic as JSONL")
    sim.add_argument("--txns", type=int, default=100, help="baseline transaction count")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument(
        "--inject",
        default="",
        help="comma list of anomalies to seed: bio_single,bio_cumulative,velocity,structuring,blacklist",
    )
    sim.add_argument(
        "--blacklist", default=None, help="path to a beneficiary blacklist (one account per line)"
    )
    sim.add_argument("--output", default=None, help="path to write JSONL (stdout if omitted)")
    sim.set_defaults(func=cmd_simulate)

    mon = sub.add_parser("monitor", help="consume JSONL transactions and emit JSONL alerts")
    mon.add_argument("--input", default=None, help="path to JSONL (stdin if omitted or '-')")
    mon.add_argument(
        "--blacklist", default=None, help="path to a beneficiary blacklist (one account per line)"
    )
    mon.add_argument("--velocity-window", dest="velocity_window", type=int, default=60)
    mon.add_argument("--velocity-threshold", dest="velocity_threshold", type=int, default=10)
    mon.add_argument(
        "--output", default=None, help="path to write alerts JSONL (stdout if omitted)"
    )
    mon.add_argument("--summary", action="store_true", help="print summary counts to stderr")
    mon.set_defaults(func=cmd_monitor)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
