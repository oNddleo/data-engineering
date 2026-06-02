"""``amlgraph`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from amlgraph import __version__

    print(f"anti-money-laundering-graph {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from amlgraph.io_jsonl import dump_accounts, dump_txns
    from amlgraph.simulator import generate

    accounts, txns = generate(
        n_accounts=args.accounts,
        n_normal_txns=args.normal,
        inject_fan_out=args.fan_out,
        inject_fan_in=args.fan_in,
        inject_layering=args.layering,
        inject_round_trip=args.round_trip,
        inject_structured=args.structured,
        seed=args.seed,
    )
    payload = {
        "accounts": [
            json.loads(line) for line in dump_accounts(accounts).splitlines() if line.strip()
        ],
        "transactions": [json.loads(line) for line in dump_txns(txns).splitlines() if line.strip()],
    }
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(
            f"wrote {len(accounts)} accounts + {len(txns)} transactions to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out)
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    from amlgraph.graph import TransactionGraph
    from amlgraph.io_jsonl import account_from_dict, dump_alerts, txn_from_dict
    from amlgraph.patterns import (
        detect_fan_in,
        detect_fan_out,
        detect_layering_chains,
        detect_round_trips,
        detect_structured_deposits,
    )

    payload = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    graph = TransactionGraph()
    for a in payload.get("accounts", []):
        graph.add_account(account_from_dict(a))
    for t in payload.get("transactions", []):
        graph.add_transaction(txn_from_dict(t))
    alerts = []
    alerts.extend(detect_fan_out(graph))
    alerts.extend(detect_fan_in(graph))
    alerts.extend(detect_layering_chains(graph))
    alerts.extend(detect_round_trips(graph))
    alerts.extend(detect_structured_deposits(graph))
    out = dump_alerts(alerts)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(alerts)} alerts to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    if args.summary:
        breakdown: dict[str, int] = {}
        for a in alerts:
            breakdown[a.kind.value] = breakdown.get(a.kind.value, 0) + 1
        sys.stderr.write(f"\nSummary: {len(alerts)} alerts — {breakdown}\n")
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    from amlgraph.graph import TransactionGraph
    from amlgraph.io_jsonl import account_from_dict, load_alerts, txn_from_dict
    from amlgraph.scoring import score_accounts, top_n

    payload = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    graph = TransactionGraph()
    for a in payload.get("accounts", []):
        graph.add_account(account_from_dict(a))
    for t in payload.get("transactions", []):
        graph.add_transaction(txn_from_dict(t))
    alerts = list(load_alerts(Path(args.alerts).read_text(encoding="utf-8")))
    scores = score_accounts(graph, alerts)
    top = top_n(scores, n=args.n)
    for r in top:
        print(f"{r.account_id}\t{r.score}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="amlgraph",
        description="In-memory AML graph + five pattern detectors for Vietnamese inter-bank flows.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic accounts+transactions dataset")
    sim.add_argument("--accounts", type=int, default=30)
    sim.add_argument("--normal", type=int, default=60)
    sim.add_argument("--fan-out", dest="fan_out", type=int, default=0)
    sim.add_argument("--fan-in", dest="fan_in", type=int, default=0)
    sim.add_argument("--layering", type=int, default=0)
    sim.add_argument("--round-trip", dest="round_trip", type=int, default=0)
    sim.add_argument("--structured", type=int, default=0)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    det = sub.add_parser("detect", help="run all five pattern detectors and dump alerts as JSONL")
    det.add_argument("--dataset", required=True)
    det.add_argument("--output", default=None)
    det.add_argument("--summary", action="store_true")
    det.set_defaults(func=cmd_detect)

    rk = sub.add_parser("rank", help="aggregate risk scores per account and print top-N")
    rk.add_argument("--dataset", required=True)
    rk.add_argument("--alerts", required=True)
    rk.add_argument("--n", type=int, default=10)
    rk.set_defaults(func=cmd_rank)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
