"""``cms`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from cms import __version__

    print(f"count-min-sketch {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from cms.simulator import StreamPattern, generate

    values = generate(
        n=args.n,
        vocab_size=args.vocab,
        pattern=StreamPattern(args.pattern),
        skew=args.skew,
        n_heavy=args.n_heavy,
        heavy_fraction=args.heavy_fraction,
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


def cmd_add(args: argparse.Namespace) -> int:
    from cms.io_jsonl import sketch_to_dict
    from cms.schema import SketchConfig
    from cms.sketch import new_sketch, update

    sketch = new_sketch(SketchConfig(epsilon=args.epsilon, delta=args.delta))
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            sketch = update(sketch, stripped)
    if args.output:
        Path(args.output).write_text(
            json.dumps(sketch_to_dict(sketch), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"wrote sketch (w={sketch.width}, d={sketch.depth}) to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(json.dumps(sketch_to_dict(sketch), ensure_ascii=False))
        sys.stdout.write("\n")
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    from cms.io_jsonl import sketch_from_dict
    from cms.sketch import estimate

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sketch = sketch_from_dict(payload)
    e = estimate(sketch, args.value)
    print(f"value:               {args.value}")
    print(f"estimated count:     {e:,}")
    print(f"total stream count:  {sketch.total_count:,}")
    print(
        "error bound (ε·N):  " f"{int(sketch.config.epsilon * sketch.total_count):,}",
    )
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    from cms.io_jsonl import sketch_from_dict, sketch_to_dict
    from cms.sketch import merge

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


def cmd_heavy(args: argparse.Namespace) -> int:
    """Two-pass top-K: build sketch from input, then rank values."""
    from cms.heavy import top_k_two_pass
    from cms.schema import SketchConfig
    from cms.sketch import new_sketch, update

    values = [
        line.strip()
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sketch = new_sketch(SketchConfig(epsilon=args.epsilon, delta=args.delta))
    for v in values:
        sketch = update(sketch, v)
    hh = top_k_two_pass(sketch, values, k=args.k)
    if args.json:
        from cms.io_jsonl import heavy_hitter_to_dict

        sys.stdout.write(
            json.dumps(
                [heavy_hitter_to_dict(h) for h in hh],
                indent=2,
                ensure_ascii=False,
            ),
        )
        sys.stdout.write("\n")
    else:
        print(f"{'rank':>4} {'value':<32} {'count':>10} {'frac%':>6}")
        for i, h in enumerate(hh, start=1):
            print(
                f"{i:>4} {h.value:<32} {h.estimated_count:>10,} "
                f"{h.fraction_of_total * 100:>5.1f}%"
            )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """One-shot: build sketch from raw values, emit stats JSON."""
    from cms.io_jsonl import stats_to_dict
    from cms.schema import SketchConfig
    from cms.sketch import new_sketch, stats, update

    sketch = new_sketch(SketchConfig(epsilon=args.epsilon, delta=args.delta))
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            sketch = update(sketch, stripped)
    sys.stdout.write(
        json.dumps(stats_to_dict(stats(sketch)), indent=2, ensure_ascii=False),
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cms",
        description="Count-Min sketches — frequency estimation at streaming scale.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic value stream")
    sim.add_argument("--n", type=int, default=10_000)
    sim.add_argument("--vocab", type=int, default=1_000)
    sim.add_argument("--pattern", choices=("UNIFORM", "ZIPF", "HEAVY_HITTERS"), default="ZIPF")
    sim.add_argument("--skew", type=float, default=1.5)
    sim.add_argument("--n-heavy", type=int, default=10)
    sim.add_argument("--heavy-fraction", type=float, default=0.6)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ad = sub.add_parser("add", help="build a sketch from a line-delimited file")
    ad.add_argument("--input", required=True)
    ad.add_argument("--epsilon", type=float, default=0.001)
    ad.add_argument("--delta", type=float, default=0.001)
    ad.add_argument("--output", default=None)
    ad.set_defaults(func=cmd_add)

    es = sub.add_parser("estimate", help="estimate frequency of one value")
    es.add_argument("--input", required=True, help="sketch JSON")
    es.add_argument("--value", required=True)
    es.set_defaults(func=cmd_estimate)

    mg = sub.add_parser("merge", help="merge multiple sketches (element-wise sum)")
    mg.add_argument("inputs", nargs="+")
    mg.add_argument("--output", default=None)
    mg.set_defaults(func=cmd_merge)

    hv = sub.add_parser("heavy", help="extract top-K heavy hitters")
    hv.add_argument("--input", required=True, help="raw values, one per line")
    hv.add_argument("--k", type=int, default=10)
    hv.add_argument("--epsilon", type=float, default=0.001)
    hv.add_argument("--delta", type=float, default=0.001)
    hv.add_argument("--json", action="store_true")
    hv.set_defaults(func=cmd_heavy)

    sm = sub.add_parser("summary", help="one-shot: build + report stats from raw values")
    sm.add_argument("--input", required=True)
    sm.add_argument("--epsilon", type=float, default=0.001)
    sm.add_argument("--delta", type=float, default=0.001)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
