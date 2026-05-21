"""CLI for VN telecom billing pipeline."""

from __future__ import annotations

import argparse
import sys

from vntelecom.billing import bill
from vntelecom.io_jsonl import dump_billed
from vntelecom.simulator import simulate_cdrs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VN telecom CDR billing CLI")
    sub = parser.add_subparsers(dest="command")

    sim_p = sub.add_parser("simulate", help="Generate and bill synthetic CDRs")
    sim_p.add_argument("--n", type=int, default=100)
    sim_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "simulate":
        cdrs = simulate_cdrs(n=args.n, seed=args.seed)
        billed = [bill(c) for c in cdrs]
        print(dump_billed(billed), end="")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
