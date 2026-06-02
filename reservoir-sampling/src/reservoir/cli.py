"""``reservoir`` CLI — sample, merge, benchmark uniformity."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from reservoir import __version__

    print(f"reservoir-sampling {__version__}")
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Sample a reservoir from a value file (one item per line)."""
    import random

    from reservoir.algorithms import sample_l, sample_r
    from reservoir.io_jsonl import dump_reservoirs

    values = [
        line.strip()
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not values:
        print("no input values", file=sys.stderr)
        return 1
    rng = random.Random(args.seed)
    if args.algorithm == "R":
        snap = sample_r(values, args.k, rng=rng)
    elif args.algorithm == "L":
        snap = sample_l(values, args.k, rng=rng)
    else:
        print(f"unknown algorithm {args.algorithm!r}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_reservoirs([snap]), encoding="utf-8")
        print(
            f"sampled {snap.n_kept}/{args.k} from {snap.n_seen} items",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(dump_reservoirs([snap]))
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """Merge two saved reservoirs into one."""
    import random

    from reservoir.io_jsonl import dump_reservoirs, load_reservoirs
    from reservoir.merge import merge_uniform

    a_list = load_reservoirs(Path(args.a).read_text(encoding="utf-8"))
    b_list = load_reservoirs(Path(args.b).read_text(encoding="utf-8"))
    if not a_list or not b_list:
        print("both files must contain at least one reservoir", file=sys.stderr)
        return 1
    rng = random.Random(args.seed)
    merged = merge_uniform(a_list[0], b_list[0], rng=rng)
    if args.output:
        Path(args.output).write_text(
            dump_reservoirs([merged]),
            encoding="utf-8",
        )
    else:
        sys.stdout.write(dump_reservoirs([merged]))
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Verify uniformity: run M independent samples, count slot frequencies."""
    import random

    from reservoir.algorithms import sample_l, sample_r
    from reservoir.simulator import uniform_stream

    if args.algorithm not in {"R", "L"}:
        print(f"unknown algorithm {args.algorithm!r}", file=sys.stderr)
        return 1

    counts: Counter[str] = Counter()
    for trial in range(args.trials):
        stream = uniform_stream(args.n)
        rng = random.Random(args.seed + trial)
        if args.algorithm == "R":
            snap = sample_r(stream, args.k, rng=rng)
        else:
            snap = sample_l(stream, args.k, rng=rng)
        counts.update(snap.items)

    total_picks = args.trials * args.k
    expected_per_item = total_picks / args.n
    min_count = min(counts.values()) if counts else 0
    max_count = max(counts.values()) if counts else 0
    payload = {
        "algorithm": args.algorithm,
        "n": args.n,
        "k": args.k,
        "trials": args.trials,
        "expected_picks_per_item": round(expected_per_item, 4),
        "min_picks": min_count,
        "max_picks": max_count,
        "distinct_items_picked": len(counts),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="reservoir",
        description="Streaming reservoir sampling — Vitter R, Li L, weighted A-Res.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    s = sub.add_parser("sample", help="sample a reservoir from a value file")
    s.add_argument("--input", required=True)
    s.add_argument("--k", type=int, required=True)
    s.add_argument("--algorithm", default="L", choices=["R", "L"])
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--output", default=None)
    s.set_defaults(func=cmd_sample)

    m = sub.add_parser("merge", help="merge two saved reservoirs")
    m.add_argument("--a", required=True)
    m.add_argument("--b", required=True)
    m.add_argument("--seed", type=int, default=0)
    m.add_argument("--output", default=None)
    m.set_defaults(func=cmd_merge)

    b = sub.add_parser("bench", help="uniformity benchmark across many trials")
    b.add_argument("--algorithm", default="R", choices=["R", "L"])
    b.add_argument("--n", type=int, default=10_000)
    b.add_argument("--k", type=int, default=100)
    b.add_argument("--trials", type=int, default=1_000)
    b.add_argument("--seed", type=int, default=0)
    b.set_defaults(func=cmd_bench)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
