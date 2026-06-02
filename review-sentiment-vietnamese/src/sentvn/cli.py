"""``sentvn`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from sentvn import __version__

    print(f"review-sentiment-vietnamese {__version__}")
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    """Classify one snippet — quick smoke test for the lexicon."""
    from sentvn.classifier import LexiconClassifier

    # `args.text is not None` (not just truthy) so `--text ""` is treated as an
    # explicit empty payload and short-circuits instead of falling through to a
    # blocked stdin read under pytest's output capture.
    raw = args.text if args.text is not None else sys.stdin.read()
    text = raw.strip()
    if not text:
        print("empty input", file=sys.stderr)
        return 2
    r = LexiconClassifier().classify_text(text)
    print(f"label={r.label.value} score={r.score} confidence={r.confidence:.2f}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from sentvn.io_jsonl import dump_reviews
    from sentvn.simulator import generate

    reviews = generate(
        n_reviews=args.reviews,
        n_sellers=args.sellers,
        n_products=args.products,
        seed=args.seed,
    )
    out = dump_reviews(reviews)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(reviews)} reviews to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_analyse(args: argparse.Namespace) -> int:
    from sentvn.classifier import LexiconClassifier
    from sentvn.io_jsonl import dump_results, load_reviews

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    clf = LexiconClassifier()
    results = [clf.classify(r) for r in load_reviews(text)]
    out = dump_results(results)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(results)} results to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    from sentvn.aggregations import by_category, by_product, by_seller, top_n, worst_n
    from sentvn.io_jsonl import load_results, load_reviews

    reviews = list(load_reviews(Path(args.reviews).read_text(encoding="utf-8")))
    results = list(load_results(Path(args.results).read_text(encoding="utf-8")))
    by_id = {r.review_id: r for r in results}
    pairs = []
    for rv in reviews:
        res = by_id.get(rv.review_id)
        if res is not None:
            pairs.append((rv, res))

    if args.by == "seller":
        buckets = by_seller(pairs)
    elif args.by == "product":
        buckets = by_product(pairs)
    else:
        buckets = by_category(pairs)

    ranked = worst_n(buckets, n=args.n) if args.worst else top_n(buckets, n=args.n)
    print(f"{'key':<22} {'n':>5} {'pos%':>7} {'neg%':>7} {'npp%':>7} {'avg_score':>10} {'avg★':>6}")
    for b in ranked:
        print(
            f"{b.key:<22} {b.n_reviews:>5} "
            f"{b.positive_pct:>6.1f}% {b.negative_pct:>6.1f}% "
            f"{b.net_promoter_pct:>+6.1f}% "
            f"{b.avg_score:>+10.2f} {b.avg_rating_x100 / 100:>6.2f}"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from sentvn.io_jsonl import load_results
    from sentvn.schema import SentimentLabel

    results = list(load_results(Path(args.results).read_text(encoding="utf-8")))
    by_label: dict[str, int] = {label.value: 0 for label in SentimentLabel}
    for r in results:
        by_label[r.label.value] += 1
    payload = {
        "n_results": len(results),
        "by_label": by_label,
        "avg_confidence": sum(r.confidence for r in results) / max(len(results), 1),
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sentvn",
        description="Vietnamese review sentiment pipeline (lexicon baseline; production swaps in PhoBERT).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    cl = sub.add_parser("classify", help="classify one snippet")
    cl.add_argument("--text", default=None)
    cl.set_defaults(func=cmd_classify)

    sim = sub.add_parser("simulate", help="emit synthetic VN reviews as JSONL")
    sim.add_argument("--reviews", type=int, default=200)
    sim.add_argument("--sellers", type=int, default=20)
    sim.add_argument("--products", type=int, default=60)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    an = sub.add_parser("analyse", help="run the lexicon classifier over a reviews JSONL")
    an.add_argument("--input", default=None)
    an.add_argument("--output", default=None)
    an.set_defaults(func=cmd_analyse)

    ag = sub.add_parser("aggregate", help="aggregate sentiment by seller/product/category")
    ag.add_argument("--reviews", required=True)
    ag.add_argument("--results", required=True)
    ag.add_argument("--by", choices=["seller", "product", "category"], default="seller")
    ag.add_argument("--n", type=int, default=10)
    ag.add_argument("--worst", action="store_true", help="rank by lowest NPP instead of highest")
    ag.set_defaults(func=cmd_aggregate)

    sm = sub.add_parser("summary", help="dump label counts + avg confidence")
    sm.add_argument("--results", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
