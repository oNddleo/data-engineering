"""CLI: kllsketch."""

from __future__ import annotations

import argparse
import json
import random
import sys


def _cmd_info(_args: argparse.Namespace) -> None:
    print(
        json.dumps(
            {
                "name": "kll-sketch",
                "version": "0.1.0",
                "description": "KLL streaming quantile sketch",
            }
        )
    )


def _cmd_demo(args: argparse.Namespace) -> None:
    from kllsketch.sketch import KLLSketch

    rng = random.Random(args.seed)
    data = [rng.gauss(0, 1) for _ in range(args.n)]
    s = KLLSketch(k=args.k)
    for v in data:
        s.update(v)

    quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
    result = {f"p{int(q*100)}": round(s.quantile(q), 4) for q in quantiles}
    result["n"] = s.n
    result["size"] = s.size()
    print(json.dumps(result))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kllsketch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info")

    dp = sub.add_parser("demo", help="Run sketch on synthetic Gaussian data")
    dp.add_argument("--n", type=int, default=10_000)
    dp.add_argument("--k", type=int, default=200)
    dp.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "info":
            _cmd_info(args)
        elif args.cmd == "demo":
            _cmd_demo(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
