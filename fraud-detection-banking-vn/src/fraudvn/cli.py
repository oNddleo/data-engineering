"""``fraudvn`` command-line interface."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from fraudvn import __version__

    print(f"fraud-detection-banking-vn {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from fraudvn.io_jsonl import dump_requests
    from fraudvn.simulator import generate

    scams = [s.strip() for s in (args.inject_scams or "").split(",") if s.strip()]
    bl = [s.strip() for s in (args.blacklist or "").split(",") if s.strip()]
    reqs = generate(
        n_benign=args.benign,
        inject_scams=scams,
        inject_blacklist=args.blacklist_n,
        inject_velocity=args.velocity,
        inject_otp_race=args.otp_race,
        inject_round_below=args.round_below,
        blacklist=bl,
        seed=args.seed,
    )
    out = dump_requests(reqs)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(reqs)} transactions to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    from fraudvn.engine import FraudEngine
    from fraudvn.io_jsonl import dump_decisions, load_requests

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    bl = [s.strip() for s in (args.blacklist or "").split(",") if s.strip()]
    engine = FraudEngine(blacklist=bl)
    decisions = engine.evaluate_many(load_requests(text))
    out = dump_decisions(decisions)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(decisions)} decisions to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    if args.summary:
        counts: dict[str, int] = {"ALLOW": 0, "REVIEW": 0, "BLOCK": 0}
        for d in decisions:
            counts[d.decision.value] = counts.get(d.decision.value, 0) + 1
        latencies = [d.latency_ms for d in decisions] or [0.0]
        sys.stderr.write(
            f"\nSummary: {len(decisions)} txns — {counts}\n"
            f"latency p50/p95/max ms: "
            f"{statistics.median(latencies):.3f} / "
            f"{_percentile(latencies, 95):.3f} / "
            f"{max(latencies):.3f}\n"
        )
    return 0


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs_sorted = sorted(xs)
    idx = int(len(xs_sorted) * p / 100)
    idx = min(idx, len(xs_sorted) - 1)
    return xs_sorted[idx]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fraudvn",
        description="Real-time fraud detection for Vietnamese internet banking.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic TransactionRequests as JSONL")
    sim.add_argument("--benign", type=int, default=50)
    sim.add_argument(
        "--inject-scams",
        dest="inject_scams",
        default="",
        help="comma list: cong_an,chuyen_nham,crypto,job_scam,loan_scam",
    )
    sim.add_argument("--blacklist-n", dest="blacklist_n", type=int, default=0)
    sim.add_argument("--velocity", type=int, default=0)
    sim.add_argument("--otp-race", dest="otp_race", type=int, default=0)
    sim.add_argument("--round-below", dest="round_below", type=int, default=0)
    sim.add_argument("--blacklist", default="", help="comma-list of beneficiary accounts")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ev = sub.add_parser("evaluate", help="run the fraud engine over JSONL transactions")
    ev.add_argument("--input", default=None)
    ev.add_argument("--blacklist", default="", help="comma-list of beneficiary accounts")
    ev.add_argument("--output", default=None)
    ev.add_argument("--summary", action="store_true")
    ev.set_defaults(func=cmd_evaluate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
