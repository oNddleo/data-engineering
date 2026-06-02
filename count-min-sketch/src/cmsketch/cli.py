"""CLI for Count-Min Sketch."""

from __future__ import annotations

import argparse
import json
import sys

from cmsketch.simulator import simulate_zipf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count-Min Sketch CLI")
    sub = parser.add_subparsers(dest="command")

    sim_p = sub.add_parser("simulate", help="Run a Zipfian stream simulation")
    sim_p.add_argument("--n-items", type=int, default=10_000)
    sim_p.add_argument("--vocab-size", type=int, default=1_000)
    sim_p.add_argument("--width", type=int, default=2048)
    sim_p.add_argument("--depth", type=int, default=5)
    sim_p.add_argument("--top-k", type=int, default=10, help="Show top-k heavy hitters")
    sim_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "simulate":
        sketch, true_counts = simulate_zipf(
            n_items=args.n_items,
            vocab_size=args.vocab_size,
            width=args.width,
            depth=args.depth,
            seed=args.seed,
        )
        # Sort true counts descending; compare with sketch estimates
        top = sorted(true_counts.items(), key=lambda x: x[1], reverse=True)[: args.top_k]
        results = []
        for item, true_c in top:
            est = sketch.query(item)
            results.append(
                {
                    "item": item,
                    "true_count": true_c,
                    "estimated_count": est,
                    "overcount": est - true_c,
                }
            )
        for r in results:
            print(json.dumps(r))
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
