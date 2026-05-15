"""``sellermart`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from sellermart import __version__

    print(f"seller-performance-data-mart {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from sellermart.io_jsonl import dump_orders, dump_returns, dump_reviews
    from sellermart.simulator import generate

    orders, returns, reviews = generate(
        n_days=args.days,
        n_sellers=args.sellers,
        n_buyers=args.buyers,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "orders.jsonl").write_text(dump_orders(orders), encoding="utf-8")
    (out_dir / "returns.jsonl").write_text(dump_returns(returns), encoding="utf-8")
    (out_dir / "reviews.jsonl").write_text(dump_reviews(reviews), encoding="utf-8")
    print(
        f"wrote {len(orders)} orders / {len(returns)} returns / "
        f"{len(reviews)} reviews to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from sellermart.etl import build_fact_seller_day
    from sellermart.io_jsonl import dump_facts, load_orders, load_returns, load_reviews

    in_dir = Path(args.in_dir)
    orders = list(load_orders((in_dir / "orders.jsonl").read_text(encoding="utf-8")))
    returns = list(load_returns((in_dir / "returns.jsonl").read_text(encoding="utf-8")))
    reviews = list(load_reviews((in_dir / "reviews.jsonl").read_text(encoding="utf-8")))
    facts = build_fact_seller_day(orders, returns, reviews)
    out_text = dump_facts(facts)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(facts)} fact rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    from sellermart.io_jsonl import load_facts
    from sellermart.kpis import seller_summary, top_sellers_by_gmv

    facts = list(load_facts(Path(args.facts).read_text(encoding="utf-8")))
    summaries = seller_summary(facts)
    rows = top_sellers_by_gmv(summaries, n=args.n)
    print(
        f"{'seller':>8} {'days':>5} {'orders':>7} {'gmv_vnd':>13} {'aov':>10} {'ret%':>6} {'avg★':>6}"
    )
    for s in rows:
        print(
            f"{s.seller_id:>8} {s.n_days_active:>5} {s.n_orders:>7} "
            f"{s.gmv_vnd:>13,} {s.aov_vnd:>10,} {s.return_rate_pct:>5.1f}% "
            f"{s.avg_rating_x100 / 100:>6.2f}"
        )
    return 0


def cmd_worst(args: argparse.Namespace) -> int:
    from sellermart.io_jsonl import load_facts
    from sellermart.kpis import seller_summary, worst_sellers_by_return_rate

    facts = list(load_facts(Path(args.facts).read_text(encoding="utf-8")))
    summaries = seller_summary(facts)
    rows = worst_sellers_by_return_rate(summaries, n=args.n, min_orders=args.min_orders)
    print(
        f"{'seller':>8} {'orders':>7} {'returns':>8} {'ret%':>7} {'refund_vnd':>13} {'refund%':>8}"
    )
    for s in rows:
        print(
            f"{s.seller_id:>8} {s.n_orders:>7} {s.n_returns:>8} "
            f"{s.return_rate_pct:>6.1f}% {s.refund_vnd:>13,} {s.refund_rate_pct:>7.1f}%"
        )
    return 0


def cmd_trend(args: argparse.Namespace) -> int:
    from sellermart.io_jsonl import load_facts
    from sellermart.kpis import daily_trend

    facts = list(load_facts(Path(args.facts).read_text(encoding="utf-8")))
    rows = daily_trend(facts)
    print(f"{'date':>10} {'orders':>7} {'units':>7} {'gmv_vnd':>13} {'returns':>8} {'ret%':>6}")
    for d in rows:
        print(
            f"{d.date_key:>10} {d.n_orders:>7} {d.n_units:>7} "
            f"{d.gmv_vnd:>13,} {d.n_returns:>8} {d.return_rate_pct:>5.1f}%"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from sellermart.io_jsonl import load_facts
    from sellermart.kpis import seller_summary

    facts = list(load_facts(Path(args.facts).read_text(encoding="utf-8")))
    summaries = seller_summary(facts)
    payload = {
        "n_fact_rows": len(facts),
        "n_sellers": len(summaries),
        "gmv_vnd_total": sum(s.gmv_vnd for s in summaries.values()),
        "n_orders_total": sum(s.n_orders for s in summaries.values()),
        "n_returns_total": sum(s.n_returns for s in summaries.values()),
        "refund_vnd_total": sum(s.refund_vnd for s in summaries.values()),
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sellermart",
        description="Star-schema data mart for VN-marketplace seller performance.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit coherent (orders, returns, reviews) JSONL")
    sim.add_argument("--days", type=int, default=14)
    sim.add_argument("--sellers", type=int, default=12)
    sim.add_argument("--buyers", type=int, default=300)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    bd = sub.add_parser("build", help="roll sources into the FactSellerDay table")
    bd.add_argument("--in-dir", required=True)
    bd.add_argument("--output", default=None)
    bd.set_defaults(func=cmd_build)

    tp = sub.add_parser("top", help="top sellers by GMV")
    tp.add_argument("--facts", required=True)
    tp.add_argument("--n", type=int, default=10)
    tp.set_defaults(func=cmd_top)

    wr = sub.add_parser("worst", help="worst sellers by return rate")
    wr.add_argument("--facts", required=True)
    wr.add_argument("--n", type=int, default=10)
    wr.add_argument("--min-orders", type=int, default=10)
    wr.set_defaults(func=cmd_worst)

    tr = sub.add_parser("trend", help="daily roll-up across all sellers")
    tr.add_argument("--facts", required=True)
    tr.set_defaults(func=cmd_trend)

    sm = sub.add_parser("summary", help="totals across the mart")
    sm.add_argument("--facts", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
