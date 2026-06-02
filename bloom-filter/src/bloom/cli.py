"""``bloom`` CLI — sizing helper, fill-and-query, FPR benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from bloom import __version__

    print(f"bloom-filter {__version__}")
    return 0


def cmd_size(args: argparse.Namespace) -> int:
    """Print optimal (size_bits, n_hashes) for a target capacity + FPR."""
    from bloom.sizing import (
        bits_per_item,
        optimal_n_hashes,
        optimal_size_bits,
    )

    m = optimal_size_bits(args.capacity, args.fpr)
    k = optimal_n_hashes(m, args.capacity)
    payload = {
        "capacity": args.capacity,
        "target_fpr": args.fpr,
        "size_bits": m,
        "size_bytes": (m + 7) // 8,
        "n_hashes": k,
        "bits_per_item": round(bits_per_item(args.fpr), 4),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build a Bloom filter from a newline-separated input file."""
    from bloom.filter import add, build, freeze
    from bloom.io_jsonl import dump_filters

    values = [
        line.strip()
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not values:
        print("no input values", file=sys.stderr)
        return 1
    capacity = args.capacity or len(values)
    bf = build(capacity, target_fpr=args.fpr)
    for v in values:
        add(bf, v)
    snapshot = freeze(bf)
    if args.output:
        Path(args.output).write_text(dump_filters([snapshot]), encoding="utf-8")
        print(
            f"wrote filter ({snapshot.size_bits} bits, {snapshot.n_items} items, "
            f"fill {snapshot.fill_ratio:.3f}) to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_filters([snapshot]))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check membership of stdin/file values against a saved filter."""
    from bloom.filter import contains
    from bloom.io_jsonl import load_filters

    snapshots = load_filters(Path(args.filter).read_text(encoding="utf-8"))
    if not snapshots:
        print("filter file is empty", file=sys.stderr)
        return 1
    bf = snapshots[0]
    queries = [
        line.strip()
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    n_hits = sum(1 for q in queries if contains(bf, q))
    payload = {
        "n_queries": len(queries),
        "n_hits": n_hits,
        "n_misses": len(queries) - n_hits,
        "hit_rate": n_hits / len(queries) if queries else 0.0,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """End-to-end FPR benchmark on synthetic data."""
    from bloom.filter import add, build, contains
    from bloom.simulator import mixed_stream
    from bloom.sizing import estimate_fpr

    positives, negatives = mixed_stream(
        args.n_positive,
        args.n_negative,
        seed=args.seed,
    )
    bf = build(args.n_positive, target_fpr=args.fpr)
    for v in positives:
        add(bf, v)
    # All positives must hit.
    pos_hits = sum(1 for v in positives if contains(bf, v))
    # Empirical FPR.
    neg_hits = sum(1 for v in negatives if contains(bf, v))
    expected = estimate_fpr(bf.size_bits, bf.n_hashes, bf.n_items)
    payload = {
        "n_positive": len(positives),
        "n_negative": len(negatives),
        "size_bits": bf.size_bits,
        "n_hashes": bf.n_hashes,
        "fill_ratio": round(bf.fill_ratio, 4),
        "expected_fpr": round(expected, 6),
        "observed_fpr": round(neg_hits / max(1, len(negatives)), 6),
        "positives_recovered": pos_hits,
        "true_positive_rate": pos_hits / max(1, len(positives)),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="bloom",
        description=("Bloom-filter toolkit — sizing, building, querying, " "and FPR benchmarking."),
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sz = sub.add_parser("size", help="optimal (m, k) for a target FPR")
    sz.add_argument("--capacity", type=int, required=True)
    sz.add_argument("--fpr", type=float, default=0.01)
    sz.set_defaults(func=cmd_size)

    bu = sub.add_parser("build", help="build a filter from a value file")
    bu.add_argument("--input", required=True)
    bu.add_argument("--capacity", type=int, default=0)
    bu.add_argument("--fpr", type=float, default=0.01)
    bu.add_argument("--output", default=None)
    bu.set_defaults(func=cmd_build)

    ck = sub.add_parser("check", help="query a saved filter")
    ck.add_argument("--filter", required=True)
    ck.add_argument("--input", required=True)
    ck.set_defaults(func=cmd_check)

    bn = sub.add_parser("bench", help="synthetic FPR benchmark")
    bn.add_argument("--n-positive", type=int, default=10_000)
    bn.add_argument("--n-negative", type=int, default=10_000)
    bn.add_argument("--fpr", type=float, default=0.01)
    bn.add_argument("--seed", type=int, default=0)
    bn.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
