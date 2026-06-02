"""``hllpp`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from hllpp import __version__

    print(f"hyperloglog-cardinality {__version__}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    from hllpp.io_jsonl import sketch_to_dict
    from hllpp.sketch import add, new_sketch

    sketch = new_sketch(precision=args.precision)
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            add(sketch, stripped)
    if args.output:
        Path(args.output).write_text(
            json.dumps(sketch_to_dict(sketch), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote sketch (p={args.precision}) to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(json.dumps(sketch_to_dict(sketch), ensure_ascii=False))
        sys.stdout.write("\n")
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    from hllpp.io_jsonl import sketch_from_dict, stats_to_dict
    from hllpp.sketch import stats

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sketch = sketch_from_dict(payload)
    summary = stats(sketch)
    if args.json:
        sys.stdout.write(
            json.dumps(stats_to_dict(summary), indent=2, ensure_ascii=False),
        )
        sys.stdout.write("\n")
    else:
        print(f"precision:                {summary.precision}")
        print(f"m (registers):            {summary.m}")
        print(f"non-zero registers:       {summary.m - summary.n_zero_registers}")
        print(f"max register value:       {summary.max_register}")
        print(f"estimated cardinality:    {summary.estimated_cardinality:,}")
        print(f"std error:                ±{summary.standard_error_pct:.2f}%")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    from hllpp.io_jsonl import sketch_from_dict, sketch_to_dict
    from hllpp.sketch import merge

    sketches = []
    for path in args.inputs:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        sketches.append(sketch_from_dict(payload))
    merged = merge(*sketches)
    if args.output:
        Path(args.output).write_text(
            json.dumps(sketch_to_dict(merged), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"merged {len(sketches)} sketches into {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(json.dumps(sketch_to_dict(merged), ensure_ascii=False))
        sys.stdout.write("\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from hllpp.simulator import StreamPattern, generate

    values = generate(
        n=args.n,
        pattern=StreamPattern(args.pattern),
        duplication=args.duplication,
        skew=args.skew,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(
            "\n".join(values) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(values)} values to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write("\n".join(values) + "\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """One-shot: read raw values, build a sketch, emit stats JSON."""
    from hllpp.io_jsonl import stats_to_dict
    from hllpp.sketch import add, new_sketch, stats

    sketch = new_sketch(precision=args.precision)
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            add(sketch, stripped)
    sys.stdout.write(
        json.dumps(stats_to_dict(stats(sketch)), indent=2, ensure_ascii=False),
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="hllpp",
        description="HyperLogLog++ sketches — distinct-count estimation at scale.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic value stream")
    sim.add_argument("--n", type=int, default=10_000)
    sim.add_argument("--pattern", choices=("UNIQUE", "DUPLICATED", "POWER_LAW"), default="UNIQUE")
    sim.add_argument("--duplication", type=int, default=5)
    sim.add_argument("--skew", type=float, default=1.5)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ad = sub.add_parser("add", help="build a sketch from a line-delimited file")
    ad.add_argument("--input", required=True)
    ad.add_argument("--precision", type=int, default=14)
    ad.add_argument("--output", default=None, help="write sketch JSON to this path")
    ad.set_defaults(func=cmd_add)

    es = sub.add_parser("estimate", help="estimate cardinality from a sketch JSON")
    es.add_argument("--input", required=True)
    es.add_argument("--json", action="store_true")
    es.set_defaults(func=cmd_estimate)

    mg = sub.add_parser("merge", help="merge multiple sketches (element-wise max)")
    mg.add_argument("inputs", nargs="+")
    mg.add_argument("--output", default=None)
    mg.set_defaults(func=cmd_merge)

    sm = sub.add_parser("summary", help="one-shot: build + estimate from raw values")
    sm.add_argument("--input", required=True)
    sm.add_argument("--precision", type=int, default=14)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
