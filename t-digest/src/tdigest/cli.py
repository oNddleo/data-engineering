"""``tdigest`` CLI — build, query quantiles, benchmark accuracy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from tdigest import __version__

    print(f"t-digest {__version__}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build a t-digest from a newline-separated input file of floats."""
    from tdigest.digest import add, build, freeze
    from tdigest.io_jsonl import dump_digests

    raw = Path(args.input).read_text(encoding="utf-8").splitlines()
    values = [float(line.strip()) for line in raw if line.strip()]
    if not values:
        print("no input values", file=sys.stderr)
        return 1
    td = build(compression=args.compression)
    for v in values:
        add(td, v)
    snap = freeze(td)
    if args.output:
        Path(args.output).write_text(dump_digests([snap]), encoding="utf-8")
        print(
            f"wrote digest ({snap.n_centroids} centroids, "
            f"{snap.total_weight:.0f} weight) to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_digests([snap]))
    return 0


def cmd_quantile(args: argparse.Namespace) -> int:
    """Query one or more quantiles from a saved digest."""
    from tdigest.digest import quantile
    from tdigest.io_jsonl import load_digests

    snaps = load_digests(Path(args.input).read_text(encoding="utf-8"))
    if not snaps:
        print("digest file is empty", file=sys.stderr)
        return 1
    td = snaps[0]
    qs = [float(q) for q in args.q]
    payload = {f"q{q}": quantile(td, q) for q in qs}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_cdf(args: argparse.Namespace) -> int:
    """Query the cdf at a value."""
    from tdigest.digest import cdf
    from tdigest.io_jsonl import load_digests

    snaps = load_digests(Path(args.input).read_text(encoding="utf-8"))
    if not snaps:
        print("digest file is empty", file=sys.stderr)
        return 1
    td = snaps[0]
    payload = {"value": args.value, "cdf": cdf(td, args.value)}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """End-to-end accuracy benchmark on a synthetic stream."""
    from tdigest.digest import add, build, freeze, quantile
    from tdigest.simulator import (
        exact_quantile,
        gaussian_stream,
        lognormal_stream,
        pareto_stream,
        uniform_stream,
    )

    values: list[float]
    if args.dist == "uniform":
        values = uniform_stream(args.n, seed=args.seed)
    elif args.dist == "gaussian":
        values = gaussian_stream(args.n, seed=args.seed)
    elif args.dist == "lognormal":
        values = lognormal_stream(args.n, seed=args.seed)
    elif args.dist == "pareto":
        values = pareto_stream(args.n, seed=args.seed)
    else:
        print(f"unknown distribution {args.dist!r}", file=sys.stderr)
        return 1
    td = build(compression=args.compression)
    for v in values:
        add(td, v)
    snap = freeze(td)

    qs = [0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999]
    rows = []
    for q in qs:
        est = quantile(snap, q)
        exact = exact_quantile(values, q)
        rel_err = abs(est - exact) / max(abs(exact), 1e-9)
        rows.append(
            {
                "q": q,
                "exact": round(exact, 6),
                "estimate": round(est, 6),
                "rel_err": round(rel_err, 6),
            }
        )
    payload = {
        "distribution": args.dist,
        "n_samples": len(values),
        "compression": args.compression,
        "n_centroids": snap.n_centroids,
        "compression_ratio": round(len(values) / max(1, snap.n_centroids), 1),
        "quantiles": rows,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="tdigest",
        description="t-digest streaming quantile sketch — build, query, bench.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    bu = sub.add_parser("build", help="build a digest from a value file")
    bu.add_argument("--input", required=True)
    bu.add_argument("--compression", type=float, default=100.0)
    bu.add_argument("--output", default=None)
    bu.set_defaults(func=cmd_build)

    qt = sub.add_parser("quantile", help="query one or more quantiles")
    qt.add_argument("--input", required=True)
    qt.add_argument("--q", nargs="+", required=True)
    qt.set_defaults(func=cmd_quantile)

    cf = sub.add_parser("cdf", help="query cdf at a value")
    cf.add_argument("--input", required=True)
    cf.add_argument("--value", type=float, required=True)
    cf.set_defaults(func=cmd_cdf)

    bn = sub.add_parser("bench", help="accuracy benchmark on synthetic data")
    bn.add_argument(
        "--dist", default="lognormal", choices=["uniform", "gaussian", "lognormal", "pareto"]
    )
    bn.add_argument("--n", type=int, default=100_000)
    bn.add_argument("--compression", type=float, default=100.0)
    bn.add_argument("--seed", type=int, default=0)
    bn.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
