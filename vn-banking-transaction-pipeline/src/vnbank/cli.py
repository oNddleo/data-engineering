"""``vnbank`` CLI — simulate, route, summarise, detect AML."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnbank import __version__

    print(f"vn-banking-transaction-pipeline {__version__}")
    return 0


def cmd_banks(_args: argparse.Namespace) -> int:
    """List bundled VN banks by deposit market share."""
    from vnbank.banks import all_profiles

    print(f"{'BIN':<8} {'ABBR':<10} {'NAME':<55} {'SHARE':>6}")
    for p in all_profiles():
        print(
            f"{p.bank.bin_code:<8} {p.bank.abbreviation:<10} "
            f"{p.bank.name_en[:55]:<55} {p.market_share_pct:>5.1f}%",
        )
    return 0


def cmd_qr(args: argparse.Namespace) -> int:
    """Build or parse a VietQR payload."""
    from vnbank.vietqr import build_vietqr, parse_vietqr

    if args.parse:
        parsed = parse_vietqr(args.parse)
        sys.stdout.write(
            json.dumps(
                {
                    "bank_bin": parsed.bank_bin,
                    "account_number": parsed.account_number,
                    "amount_vnd": parsed.amount_vnd,
                    "purpose": parsed.purpose,
                    "is_dynamic": parsed.is_dynamic,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        return 0
    payload = build_vietqr(
        bank_bin=args.bank_bin,
        account_number=args.account_number,
        amount_vnd=args.amount,
        purpose=args.purpose or "",
    )
    print(payload)
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnbank.io_jsonl import dump_txns
    from vnbank.simulator import generate

    txns = generate(
        n_accounts=args.accounts,
        n_days=args.days,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_txns(txns), encoding="utf-8")
        print(
            f"wrote {len(txns)} transactions to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_txns(txns))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from vnbank.io_jsonl import dump_summaries, load_txns
    from vnbank.summary import aggregate_daily

    txns = load_txns(Path(args.input).read_text(encoding="utf-8"))
    summaries = aggregate_daily(txns)
    if args.output:
        Path(args.output).write_text(dump_summaries(summaries), encoding="utf-8")
        print(
            f"wrote {len(summaries)} daily summaries to {args.output}",
            file=sys.stderr,
        )
    if args.show:
        print(
            f"{'date':<12} {'account':<16} {'bank':<8} "
            f"{'#txn':>5} {'debit_vnd':>14} {'credit_vnd':>14}",
        )
        for s in summaries[: args.show]:
            print(
                f"{s.date:<12} {s.account_number:<16} {s.bank_bin:<8} "
                f"{s.n_txns:>5} {s.total_debit_vnd:>14,} "
                f"{s.total_credit_vnd:>14,}",
            )
    return 0


def cmd_aml(args: argparse.Namespace) -> int:
    from vnbank.aml import find_ctr, find_high_velocity, find_structuring
    from vnbank.io_jsonl import load_txns

    txns = load_txns(Path(args.input).read_text(encoding="utf-8"))
    ctr = find_ctr(txns)
    struct = find_structuring(txns)
    vel = find_high_velocity(txns)
    print(f"CTR_CASH_THRESHOLD ({len(ctr)}):")
    for f in ctr[: args.show]:
        print(f"  {f.account_number:<16} {f.bank_bin:<8} {f.detail}")
    print(f"STRUCTURING ({len(struct)}):")
    for f in struct[: args.show]:
        print(f"  {f.account_number:<16} {f.bank_bin:<8} {f.detail}")
    print(f"HIGH_VELOCITY ({len(vel)}):")
    for f in vel[: args.show]:
        print(f"  {f.account_number:<16} {f.bank_bin:<8} {f.detail}")
    return 0 if not (ctr or struct or vel) else 2


def cmd_route(args: argparse.Namespace) -> int:
    """Show routing decision for a transfer."""
    from vnbank.routing import route

    decision = route(args.sender_bin, args.receiver_bin, args.amount)
    payload = {
        "sender_bin": args.sender_bin,
        "receiver_bin": args.receiver_bin,
        "amount_vnd": args.amount,
        "rail": decision.rail.value,
        "fee_vnd": decision.fee_vnd,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnbank",
        description="VN banking transaction pipeline — routing, summaries, AML.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("banks").set_defaults(func=cmd_banks)

    qr = sub.add_parser("qr", help="build or parse a VietQR payload")
    qr.add_argument("--parse", default=None)
    qr.add_argument("--bank-bin")
    qr.add_argument("--account-number")
    qr.add_argument("--amount", type=int, default=0)
    qr.add_argument("--purpose", default=None)
    qr.set_defaults(func=cmd_qr)

    sim = sub.add_parser("simulate", help="emit a synthetic transaction stream")
    sim.add_argument("--accounts", type=int, default=30)
    sim.add_argument("--days", type=int, default=30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    sm = sub.add_parser("summary", help="aggregate transactions into daily summaries")
    sm.add_argument("--input", required=True)
    sm.add_argument("--output", default=None)
    sm.add_argument("--show", type=int, default=10)
    sm.set_defaults(func=cmd_summary)

    aml = sub.add_parser("aml", help="detect CTR, structuring, high-velocity patterns")
    aml.add_argument("--input", required=True)
    aml.add_argument("--show", type=int, default=5)
    aml.set_defaults(func=cmd_aml)

    rt = sub.add_parser("route", help="show routing decision for a transfer")
    rt.add_argument("--sender-bin", required=True)
    rt.add_argument("--receiver-bin", required=True)
    rt.add_argument("--amount", type=int, required=True)
    rt.set_defaults(func=cmd_route)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
