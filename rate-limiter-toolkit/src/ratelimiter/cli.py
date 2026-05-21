"""CLI for rate limiter toolkit."""

from __future__ import annotations

import argparse
import json
import sys

from ratelimiter.simulator import simulate_sliding_window, simulate_token_bucket


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rate limiter toolkit CLI")
    sub = parser.add_subparsers(dest="command")

    tb_p = sub.add_parser("token-bucket", help="Simulate token bucket rate limiter")
    tb_p.add_argument("--capacity", type=float, default=10.0)
    tb_p.add_argument("--refill-rate", type=float, default=5.0)
    tb_p.add_argument("--n-requests", type=int, default=100)
    tb_p.add_argument("--interval", type=float, default=0.1)

    sw_p = sub.add_parser("sliding-window", help="Simulate sliding window rate limiter")
    sw_p.add_argument("--limit", type=int, default=10)
    sw_p.add_argument("--window", type=float, default=1.0)
    sw_p.add_argument("--n-requests", type=int, default=100)
    sw_p.add_argument("--interval", type=float, default=0.05)

    args = parser.parse_args(argv)

    if args.command == "token-bucket":
        result = simulate_token_bucket(
            capacity=args.capacity,
            refill_rate=args.refill_rate,
            n_requests=args.n_requests,
            request_interval_s=args.interval,
        )
    elif args.command == "sliding-window":
        result = simulate_sliding_window(
            limit=args.limit,
            window_s=args.window,
            n_requests=args.n_requests,
            request_interval_s=args.interval,
        )
    else:
        parser.print_help()
        return 1

    print(
        json.dumps(
            {
                "algorithm": result.algorithm,
                "total_requests": result.total_requests,
                "allowed": result.allowed,
                "rejected": result.rejected,
                "allow_rate_pct": round(result.allowed / result.total_requests * 100, 1),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
