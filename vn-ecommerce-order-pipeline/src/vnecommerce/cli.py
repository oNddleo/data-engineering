"""CLI for VN e-commerce order pipeline."""

from __future__ import annotations

import argparse
import sys

from vnecommerce.io_jsonl import dump_normalised
from vnecommerce.normaliser import normalise
from vnecommerce.simulator import simulate_orders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VN e-commerce order pipeline CLI")
    sub = parser.add_subparsers(dest="command")

    sim_p = sub.add_parser("simulate", help="Generate and normalise synthetic orders")
    sim_p.add_argument("--n", type=int, default=100)
    sim_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "simulate":
        raw_orders = simulate_orders(n=args.n, seed=args.seed)
        normalised = [normalise(o) for o in raw_orders]
        print(dump_normalised(normalised), end="")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
