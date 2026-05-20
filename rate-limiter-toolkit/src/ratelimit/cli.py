"""``ratelimit`` CLI — benchmark three rate-limiter algorithms."""

from __future__ import annotations

import argparse
import json
import sys


def cmd_info(_args: argparse.Namespace) -> int:
    from ratelimit import __version__

    print(f"rate-limiter-toolkit {__version__}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Run an algorithm against a synthetic stream and report admit rate."""
    from ratelimit.leaky_bucket import allow as leaky_allow
    from ratelimit.schema import LeakyBucket, SlidingWindowLog, TokenBucket
    from ratelimit.simulator import burst_then_idle, constant_rate
    from ratelimit.sliding_window import allow as sliding_allow
    from ratelimit.token_bucket import allow as token_allow

    if args.burst:
        stream = burst_then_idle(
            n_keys=args.keys,
            n_bursts=args.n_bursts,
            burst_size=args.burst_size,
            seed=args.seed,
        )
    else:
        stream = constant_rate(
            n_keys=args.keys,
            n_requests=args.requests,
            interval_ms=args.interval_ms,
            seed=args.seed,
        )

    if args.algorithm == "token":
        tb = TokenBucket(capacity=args.capacity, rate_per_sec=args.rate)
        admitted = sum(1 for k, t in stream if token_allow(tb, k, t))
    elif args.algorithm == "leaky":
        lb = LeakyBucket(capacity=args.capacity, rate_per_sec=args.rate)
        admitted = sum(1 for k, t in stream if leaky_allow(lb, k, t))
    elif args.algorithm == "sliding":
        sw = SlidingWindowLog(capacity=args.capacity, window_ms=args.window_ms)
        admitted = sum(1 for k, t in stream if sliding_allow(sw, k, t))
    else:
        print(f"unknown algorithm {args.algorithm!r}", file=sys.stderr)
        return 1

    payload = {
        "algorithm": args.algorithm,
        "n_requests": len(stream),
        "n_admitted": admitted,
        "n_throttled": len(stream) - admitted,
        "admit_rate": admitted / max(1, len(stream)),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="ratelimit",
        description="Rate-limiter toolkit — token bucket, leaky bucket, sliding window.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    b = sub.add_parser("bench", help="benchmark an algorithm on a synthetic stream")
    b.add_argument("--algorithm", default="token", choices=["token", "leaky", "sliding"])
    b.add_argument("--capacity", type=int, default=10)
    b.add_argument("--rate", type=float, default=10.0)
    b.add_argument("--window-ms", type=int, default=1_000)
    b.add_argument("--keys", type=int, default=3)
    b.add_argument("--requests", type=int, default=100)
    b.add_argument("--interval-ms", type=int, default=100)
    b.add_argument("--burst", action="store_true")
    b.add_argument("--n-bursts", type=int, default=5)
    b.add_argument("--burst-size", type=int, default=20)
    b.add_argument("--seed", type=int, default=0)
    b.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
