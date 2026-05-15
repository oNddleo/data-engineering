"""``clvseg`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from clvseg import __version__

    print(f"customer-lifetime-value-segmenter {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from clvseg.io_jsonl import dump_customers, dump_orders
    from clvseg.simulator import generate

    customers, orders, as_of = generate(
        n_customers=args.customers,
        window_days=args.window_days,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "customers.jsonl").write_text(dump_customers(customers), encoding="utf-8")
    (out_dir / "orders.jsonl").write_text(dump_orders(orders), encoding="utf-8")
    (out_dir / "as_of.txt").write_text(as_of.isoformat(), encoding="utf-8")
    print(
        f"wrote {len(customers)} customers + {len(orders)} orders to {out_dir}/ (as_of={as_of.isoformat()})",
        file=sys.stderr,
    )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from clvseg.io_jsonl import dump_scores, load_customers, load_orders
    from clvseg.rfm import score

    in_dir = Path(args.in_dir)
    customers = list(load_customers((in_dir / "customers.jsonl").read_text(encoding="utf-8")))
    orders = list(load_orders((in_dir / "orders.jsonl").read_text(encoding="utf-8")))
    as_of = datetime.fromisoformat((in_dir / "as_of.txt").read_text(encoding="utf-8").strip())
    scores = score(customers, orders, as_of)
    out = dump_scores(scores)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(scores)} RFM scores to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_segment(args: argparse.Namespace) -> int:
    from clvseg.io_jsonl import load_scores
    from clvseg.segments import classify_all, segment_distribution

    scores = list(load_scores(Path(args.scores).read_text(encoding="utf-8")))
    assignments = classify_all(scores)
    dist = segment_distribution(assignments)
    total = sum(dist.values()) or 1
    print(f"{'segment':<22} {'count':>7} {'pct':>7}")
    for seg, count in dist.items():
        pct = count / total * 100
        print(f"{seg.value:<22} {count:>7} {pct:>6.1f}%")
    return 0


def cmd_clv(args: argparse.Namespace) -> int:
    from clvseg.clv import forecast, top_clv, total_clv_by_segment
    from clvseg.io_jsonl import dump_clvs, load_scores
    from clvseg.segments import classify_all

    scores = list(load_scores(Path(args.scores).read_text(encoding="utf-8")))
    assignments = classify_all(scores)
    forecasts = forecast(scores, assignments, window_days=args.window_days)
    if args.output:
        Path(args.output).write_text(dump_clvs(forecasts), encoding="utf-8")
        print(f"wrote {len(forecasts)} CLV forecasts to {args.output}", file=sys.stderr)
    if args.show_top:
        print(f"{'customer':<10} {'segment':<22} {'aov':>10} {'freq':>5} {'forecast':>15}")
        for f in top_clv(forecasts, n=args.show_top):
            print(
                f"{f.customer_id:<10} {f.segment.value:<22} "
                f"{f.historical_aov_vnd:>10,} {f.historical_frequency:>5} "
                f"{f.forecast_vnd:>15,}"
            )
    by_seg = total_clv_by_segment(forecasts)
    print(f"\n{'segment':<22} {'total_clv_vnd':>20}")
    for seg, val in by_seg.items():
        print(f"{seg.value:<22} {val:>20,}")
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    from clvseg.io_jsonl import load_scores
    from clvseg.schema import Segment
    from clvseg.segments import classify_all, top_in_segment

    scores = list(load_scores(Path(args.scores).read_text(encoding="utf-8")))
    assignments = classify_all(scores)
    target = Segment(args.segment)
    rows = top_in_segment(scores, assignments, target, n=args.n)
    print(f"{'customer':<10} {'rfm':>4} {'recency':>8} {'freq':>5} {'monetary':>14}")
    for s in rows:
        print(
            f"{s.customer_id:<10} {s.rfm_string:>4} {s.recency_days:>8} "
            f"{s.frequency:>5} {s.monetary_vnd:>14,}"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from clvseg.io_jsonl import load_scores
    from clvseg.schema import Segment
    from clvseg.segments import classify_all, segment_distribution

    scores = list(load_scores(Path(args.scores).read_text(encoding="utf-8")))
    assignments = classify_all(scores)
    dist = segment_distribution(assignments)
    payload = {
        "n_customers": len(scores),
        "by_segment": {seg.value: dist[seg] for seg in Segment},
        "total_monetary_vnd": sum(s.monetary_vnd for s in scores),
        "total_frequency": sum(s.frequency for s in scores),
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="clvseg",
        description="RFM + named-segment + CLV forecast for VN-marketplace customers.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic customers + orders")
    sim.add_argument("--customers", type=int, default=500)
    sim.add_argument("--window-days", type=int, default=180)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    sc = sub.add_parser("score", help="compute RFM scores")
    sc.add_argument("--in-dir", required=True)
    sc.add_argument("--output", default=None)
    sc.set_defaults(func=cmd_score)

    seg = sub.add_parser("segment", help="distribution of customers across CRM segments")
    seg.add_argument("--scores", required=True)
    seg.set_defaults(func=cmd_segment)

    cl = sub.add_parser("clv", help="forecast CLV per customer + roll up by segment")
    cl.add_argument("--scores", required=True)
    cl.add_argument("--window-days", type=int, default=180)
    cl.add_argument("--output", default=None)
    cl.add_argument("--show-top", type=int, default=0)
    cl.set_defaults(func=cmd_clv)

    tp = sub.add_parser("top", help="top customers within a segment by monetary")
    tp.add_argument("--scores", required=True)
    tp.add_argument("--segment", required=True)
    tp.add_argument("--n", type=int, default=10)
    tp.set_defaults(func=cmd_top)

    sm = sub.add_parser("summary", help="JSON summary of segment + monetary totals")
    sm.add_argument("--scores", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
