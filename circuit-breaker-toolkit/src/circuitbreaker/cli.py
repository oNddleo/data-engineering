"""CLI for circuit breaker toolkit."""

from __future__ import annotations

import argparse
import json
import sys

from circuitbreaker.simulator import simulate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Circuit breaker toolkit CLI")
    sub = parser.add_subparsers(dest="command")

    sim_p = sub.add_parser("simulate", help="Simulate a failure pattern")
    sim_p.add_argument("--failure-rate", type=float, default=0.6)
    sim_p.add_argument("--n-calls", type=int, default=50)
    sim_p.add_argument("--failure-threshold", type=int, default=3)
    sim_p.add_argument("--success-threshold", type=int, default=2)
    sim_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.command == "simulate":
        result = simulate(
            failure_rate=args.failure_rate,
            n_calls=args.n_calls,
            failure_threshold=args.failure_threshold,
            success_threshold=args.success_threshold,
            seed=args.seed,
        )
        out = {
            "total_calls": result.total_calls,
            "successful_calls": result.successful_calls,
            "failed_calls": result.failed_calls,
            "rejected_calls": result.rejected_calls,
            "final_state": result.final_state.value,
            "state_transitions": result.state_transitions,
        }
        print(json.dumps(out))
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
