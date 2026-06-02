"""``fxagg`` command-line interface."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from fxagg import __version__

    print(f"vietcombank-bidv-techcombank-fx-rate-aggregator {__version__}")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from fxagg.parsers import (
        parse_bidv_html,
        parse_generic_csv,
        parse_techcombank_json,
        parse_vietcombank_xml,
    )
    from fxagg.schema import VN_TZ, Bank

    text = (
        sys.stdin.read()
        if args.file in (None, "-")
        else Path(args.file).read_text(encoding="utf-8")
    )
    fmt = args.format.lower()
    if fmt == "vcb-xml":
        snap = parse_vietcombank_xml(text)
    elif fmt == "bidv-html":
        ts = datetime.fromisoformat(args.quoted_at) if args.quoted_at else datetime.now(tz=VN_TZ)
        snap = parse_bidv_html(text, quoted_at=ts)
    elif fmt == "tcb-json":
        snap = parse_techcombank_json(text)
    elif fmt == "generic-csv":
        if not args.bank:
            print("generic-csv requires --bank", file=sys.stderr)
            return 2
        ts = datetime.fromisoformat(args.quoted_at) if args.quoted_at else datetime.now(tz=VN_TZ)
        snap = parse_generic_csv(text, bank=Bank(args.bank.upper()), quoted_at=ts)
    else:
        print(f"unknown format: {fmt}", file=sys.stderr)
        return 2
    print(f"{snap.bank.value} @ {snap.quoted_at.isoformat()}  ({len(snap.quotes)} quotes)")
    for q in snap.quotes:
        cash = f" cash={q.buy_cash_vnd:,}" if q.buy_cash_vnd is not None else ""
        print(
            f"  {q.currency.value}  buy={q.buy_transfer_vnd:,}  sell={q.sell_vnd:,}{cash}  "
            f"spread={q.bid_ask_spread_pct:.2f}%"
        )
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from fxagg.schema import VN_TZ, Currency
    from fxagg.spread import analyze
    from fxagg.storage import load_store

    store = load_store(Path(args.store))
    currency = Currency(args.currency.upper())
    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of)
        quotes = store.as_of(currency, as_of)
    else:
        quotes = store.all_latest(currency)
        as_of = max((q.quoted_at for q in quotes.values()), default=datetime.now(tz=VN_TZ))
    analysis = analyze(
        quotes,
        outlier_pct=args.outlier_pct,
        stale_threshold_min=args.stale_min,
        reference_time=as_of,
    )
    print(f"=== {currency.value} cross-bank analysis @ {as_of.isoformat()} ===")
    print(
        f"banks: {len(quotes)}   median buy={analysis.median_buy_transfer:,}   "
        f"median sell={analysis.median_sell:,}   median spread={analysis.median_bid_ask_pct:.2f}%"
    )
    for bank, q in sorted(analysis.bank_quotes.items(), key=lambda kv: kv[0].value):
        print(
            f"  {bank.value:<5} buy={q.buy_transfer_vnd:,}  sell={q.sell_vnd:,}  "
            f"spread={q.bid_ask_spread_pct:.2f}%  ts={q.quoted_at.isoformat()}"
        )
    if analysis.alerts:
        print("\nAlerts:")
        for a in analysis.alerts:
            print(f"  [{a.severity.value}] {a.kind.value} {a.bank.value}: {a.detail}")
    else:
        print("\nNo alerts.")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from fxagg.schema import Bank, Currency
    from fxagg.simulator import generate
    from fxagg.storage import dump_quotes

    banks = [Bank(b.upper()) for b in args.banks.split(",") if b.strip()]
    currencies = [Currency(c.upper()) for c in args.currencies.split(",") if c.strip()]
    anomalies = [a.strip() for a in (args.inject or "").split(",") if a.strip()]
    quotes = generate(
        banks=banks,
        currencies=currencies,
        n_snapshots=args.snapshots,
        interval_minutes=args.interval,
        seed=args.seed,
        inject_anomalies=anomalies,
    )
    out = dump_quotes(quotes)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(quotes)} quotes to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fxagg",
        description="Aggregate FX rates published by Vietnamese banks and detect spread anomalies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    pp = sub.add_parser("parse", help="parse one vendor payload and dump the snapshot")
    pp.add_argument(
        "--format",
        required=True,
        choices=["vcb-xml", "bidv-html", "tcb-json", "generic-csv"],
    )
    pp.add_argument("--file", default=None)
    pp.add_argument("--bank", default=None, help="required for generic-csv")
    pp.add_argument(
        "--quoted-at",
        dest="quoted_at",
        default=None,
        help="ISO-8601 timestamp; needed for bidv-html and generic-csv",
    )
    pp.set_defaults(func=cmd_parse)

    an = sub.add_parser("analyze", help="cross-bank analysis of one currency")
    an.add_argument("--store", required=True, help="path to JSONL store")
    an.add_argument("--currency", required=True)
    an.add_argument("--as-of", dest="as_of", default=None, help="ISO-8601 timestamp")
    an.add_argument("--outlier-pct", dest="outlier_pct", type=float, default=1.0)
    an.add_argument("--stale-min", dest="stale_min", type=int, default=30)
    an.set_defaults(func=cmd_analyze)

    sim = sub.add_parser("simulate", help="emit synthetic FX quotes JSONL")
    sim.add_argument("--banks", default="VCB,BIDV,TCB,MB,VPB")
    sim.add_argument("--currencies", default="USD,EUR,JPY")
    sim.add_argument("--snapshots", type=int, default=3)
    sim.add_argument("--interval", type=int, default=5, help="minutes between snapshots")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument(
        "--inject",
        default="",
        help="comma list of anomalies: outlier_buy,outlier_sell,inverted,stale",
    )
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
