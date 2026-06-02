"""CLI for HyperLogLog sketch."""

from __future__ import annotations

import argparse
import json
import sys

from hllsketch.simulator import simulate_distinct


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HyperLogLog cardinality estimator CLI")
    sub = parser.add_subparsers(dest="command")

    sim_p = sub.add_parser("simulate", help="Simulate a stream and estimate cardinality")
    sim_p.add_argument("--n-distinct", type=int, default=10_000)
    sim_p.add_argument("--repetitions", type=int, default=3)
    sim_p.add_argument("--precision", type=int, default=12)
    sim_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "simulate":
        hll, true_distinct = simulate_distinct(
            n_distinct=args.n_distinct,
            repetitions=args.repetitions,
            precision=args.precision,
            seed=args.seed,
        )
        estimated = hll.count()
        error_pct = abs(estimated - true_distinct) / true_distinct * 100
        result = {
            "true_distinct": true_distinct,
            "estimated_distinct": estimated,
            "error_pct": round(error_pct, 2),
            "precision": args.precision,
            "num_registers": hll.num_registers,
            "size_bytes": hll.size_bytes(),
        }
        print(json.dumps(result))
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
