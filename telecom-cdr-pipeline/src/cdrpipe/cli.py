"""``cdrpipe`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from cdrpipe import __version__

    print(f"telecom-cdr-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from cdrpipe.io_jsonl import dump_cdrs
    from cdrpipe.simulator import generate

    cdrs = generate(n_subscribers=args.subscribers, n_days=args.days, seed=args.seed)
    if args.output:
        Path(args.output).write_text(dump_cdrs(cdrs), encoding="utf-8")
        print(f"wrote {len(cdrs)} CDRs to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_cdrs(cdrs))
    return 0


def cmd_rate(args: argparse.Namespace) -> int:
    from cdrpipe.io_jsonl import dump_rated, load_cdrs
    from cdrpipe.rating import rate

    cdrs = load_cdrs(Path(args.input).read_text(encoding="utf-8"))
    rated = [rate(c) for c in cdrs]
    if args.output:
        Path(args.output).write_text(dump_rated(rated), encoding="utf-8")
        print(f"wrote {len(rated)} rated CDRs to {args.output}", file=sys.stderr)
    if args.show:
        print(f"{'cdr':<14} {'kind':<5} {'carrier':<13} {'amount':>10} {'vat':>8}")
        for r in rated[: args.show]:
            print(
                f"{r.cdr.cdr_id:<14} {r.cdr.kind.value:<5} "
                f"{r.subscriber_carrier.value:<13} "
                f"{r.rated_amount_vnd:>10,} {r.vat_amount_vnd:>8,}",
            )
    return 0


def cmd_bill(args: argparse.Namespace) -> int:
    from cdrpipe.billing import aggregate_bills
    from cdrpipe.io_jsonl import dump_bills, load_cdrs
    from cdrpipe.rating import rate

    cdrs = load_cdrs(Path(args.input).read_text(encoding="utf-8"))
    rated = [rate(c) for c in cdrs]
    bills = aggregate_bills(rated)
    if args.output:
        Path(args.output).write_text(dump_bills(bills), encoding="utf-8")
        print(f"wrote {len(bills)} bills to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'subscriber':<12} {'carrier':<13} {'month':<8} "
            f"{'voice_s':>8} {'sms':>5} {'mb':>6} {'total_vnd':>12}"
        )
        for b in bills[: args.show]:
            mb_used = b.total_bytes // (1024 * 1024)
            print(
                f"{b.subscriber_msisdn:<12} {b.carrier.value:<13} "
                f"{b.billing_month:<8} {b.total_voice_seconds:>8} "
                f"{b.total_sms:>5} {mb_used:>6} {b.total_amount_vnd:>12,}",
            )
    return 0


def cmd_fraud(args: argparse.Namespace) -> int:
    from cdrpipe.fraud import (
        find_foreign_roaming,
        find_premium_rate_spikes,
        find_sim_swap,
    )
    from cdrpipe.io_jsonl import load_cdrs
    from cdrpipe.rating import rate

    cdrs = load_cdrs(Path(args.input).read_text(encoding="utf-8"))
    rated = [rate(c) for c in cdrs]
    premium = find_premium_rate_spikes(
        rated,
        min_premium_minutes_per_day=args.min_premium_minutes,
    )
    roaming = find_foreign_roaming(
        rated,
        min_roaming_amount_vnd=args.min_roaming_amount,
    )
    swap = find_sim_swap(cdrs, min_jaccard=args.min_jaccard)
    print(f"PREMIUM_RATE_SPIKE ({len(premium)}):")
    for f in premium[: args.show]:
        print(f"  {f.subscriber_msisdn:<12} {f.carrier.value:<13} {f.detail}")
    print(f"FOREIGN_ROAMING ({len(roaming)}):")
    for f in roaming[: args.show]:
        print(f"  {f.subscriber_msisdn:<12} {f.carrier.value:<13} {f.detail}")
    print(f"SIM_SWAP ({len(swap)}):")
    for f in swap[: args.show]:
        print(f"  {f.subscriber_msisdn:<12} {f.carrier.value:<13} {f.detail}")
    return 0 if not (premium or roaming or swap) else 2


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from cdrpipe.billing import aggregate_bills
    from cdrpipe.fraud import (
        find_foreign_roaming,
        find_premium_rate_spikes,
        find_sim_swap,
    )
    from cdrpipe.io_jsonl import load_cdrs
    from cdrpipe.rating import rate

    cdrs = load_cdrs(Path(args.input).read_text(encoding="utf-8"))
    rated = [rate(c) for c in cdrs]
    bills = aggregate_bills(rated)
    premium = find_premium_rate_spikes(rated)
    roaming = find_foreign_roaming(rated)
    swap = find_sim_swap(cdrs)
    by_kind: Counter[str] = Counter()
    for c in cdrs:
        by_kind[c.kind.value] += 1
    by_carrier: Counter[str] = Counter()
    for r in rated:
        by_carrier[r.subscriber_carrier.value] += 1
    total_revenue = sum(b.total_amount_vnd for b in bills)
    payload = {
        "n_cdrs": len(cdrs),
        "n_subscribers": len({c.subscriber_msisdn for c in cdrs}),
        "n_bills": len(bills),
        "cdrs_by_kind": dict(sorted(by_kind.items())),
        "cdrs_by_carrier": dict(sorted(by_carrier.items())),
        "total_revenue_vnd": total_revenue,
        "n_premium_findings": len(premium),
        "n_roaming_findings": len(roaming),
        "n_sim_swap_findings": len(swap),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cdrpipe",
        description="VN telecom CDR rating, billing, and fraud detection.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic CDR stream")
    sim.add_argument("--subscribers", type=int, default=50)
    sim.add_argument("--days", type=int, default=30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    rt = sub.add_parser("rate", help="apply tariff → RatedCDR records")
    rt.add_argument("--input", required=True)
    rt.add_argument("--output", default=None)
    rt.add_argument("--show", type=int, default=10)
    rt.set_defaults(func=cmd_rate)

    bl = sub.add_parser("bill", help="aggregate rated CDRs into monthly bills")
    bl.add_argument("--input", required=True)
    bl.add_argument("--output", default=None)
    bl.add_argument("--show", type=int, default=10)
    bl.set_defaults(func=cmd_bill)

    fr = sub.add_parser("fraud", help="detect premium-rate, roaming, SIM-swap")
    fr.add_argument("--input", required=True)
    fr.add_argument("--min-premium-minutes", type=int, default=30)
    fr.add_argument("--min-roaming-amount", type=int, default=100_000)
    fr.add_argument("--min-jaccard", type=float, default=0.10)
    fr.add_argument("--show", type=int, default=5)
    fr.set_defaults(func=cmd_fraud)

    sm = sub.add_parser("summary", help="JSON roll-up of pipeline run")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
