"""``vnbhyt`` CLI: info | payout | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vnbhyt.io_jsonl import dump_claims, dump_payouts, load_claims
from vnbhyt.payout import compute
from vnbhyt.simulator import generate


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "vn-insurance-claim-pipeline",
                "version": "0.1.0",
                "subcommands": ["info", "payout", "simulate"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    claims = generate(n=ns.n, seed=ns.seed)
    Path(ns.output).write_text(dump_claims(claims), encoding="utf-8")
    print(json.dumps({"count": len(claims), "output": ns.output}))
    return 0


def _cmd_payout(ns: argparse.Namespace) -> int:
    claims = load_claims(Path(ns.input).read_text(encoding="utf-8"))
    payouts = [compute(c) for c in claims]
    Path(ns.output).write_text(dump_payouts(payouts), encoding="utf-8")
    total = sum(p.insurance_payout_vnd for p in payouts)
    print(
        json.dumps(
            {
                "count": len(payouts),
                "total_insurance_payout_vnd": total,
                "total_patient_copay_vnd": sum(p.patient_copay_vnd for p in payouts),
            }
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vnbhyt")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=100)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    pay = sub.add_parser("payout")
    pay.add_argument("--input", required=True)
    pay.add_argument("--output", required=True)
    pay.set_defaults(func=_cmd_payout)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
