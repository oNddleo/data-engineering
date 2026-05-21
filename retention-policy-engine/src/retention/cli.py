"""CLI: retention."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_info(_args: argparse.Namespace) -> None:
    print(
        json.dumps(
            {
                "name": "retention-policy-engine",
                "version": "0.1.0",
                "policy_kinds": ["TTL", "MAX_COUNT", "MAX_SIZE", "COMPOSITE"],
            }
        )
    )


def _cmd_simulate(args: argparse.Namespace) -> None:
    from retention.engine import apply_policy
    from retention.policy import Policy
    from retention.simulator import generate, summarise

    records = generate(n=args.n, seed=args.seed, now_ms=args.now_ms)
    before = summarise(records)

    if args.policy == "ttl":
        policy = Policy.ttl(ttl_ms=args.ttl_ms)
    elif args.policy == "max-count":
        policy = Policy.max_count(n=args.max_count)
    elif args.policy == "max-size":
        policy = Policy.max_size(max_bytes=args.max_bytes)
    else:
        print(f"Unknown policy: {args.policy}", file=sys.stderr)
        sys.exit(1)

    result = apply_policy(records, policy, now_ms=args.now_ms)
    print(
        json.dumps(
            {
                "before": {"n": before.n_records, "total_bytes": before.total_bytes},
                "evicted": result.records_freed,
                "bytes_freed": result.bytes_freed,
                "kept": len(result.kept),
            }
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="retention")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info")

    sp = sub.add_parser("simulate")
    sp.add_argument("--n", type=int, default=100)
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--now-ms", type=int, default=1_000_000_000, dest="now_ms")
    sp.add_argument("--policy", choices=["ttl", "max-count", "max-size"], default="ttl")
    sp.add_argument("--ttl-ms", type=int, default=3_600_000, dest="ttl_ms")
    sp.add_argument("--max-count", type=int, default=50, dest="max_count")
    sp.add_argument("--max-bytes", type=int, default=10_000_000, dest="max_bytes")

    args = parser.parse_args(argv)
    if args.cmd == "info":
        _cmd_info(args)
    elif args.cmd == "simulate":
        _cmd_simulate(args)


if __name__ == "__main__":
    main()
