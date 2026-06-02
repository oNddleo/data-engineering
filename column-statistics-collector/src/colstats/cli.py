"""``colstats`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from colstats import __version__

    print(f"column-statistics-collector {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from colstats.simulator import (
        NumericShape,
        generate_categorical,
        generate_date,
        generate_numeric,
        generate_string,
    )

    if args.kind == "NUMERIC":
        values = generate_numeric(
            n=args.rows,
            shape=NumericShape(args.shape),
            mean=args.mean,
            std=args.std,
            null_fraction=args.null_fraction,
            seed=args.seed,
        )
    elif args.kind == "CATEGORICAL":
        values = generate_categorical(
            n=args.rows,
            n_categories=args.categories,
            skew=args.skew,
            null_fraction=args.null_fraction,
            seed=args.seed,
        )
    elif args.kind == "STRING":
        values = generate_string(
            n=args.rows,
            length=args.length,
            null_fraction=args.null_fraction,
            seed=args.seed,
        )
    elif args.kind == "DATE":
        values = generate_date(
            n=args.rows,
            span_days=args.span_days,
            null_fraction=args.null_fraction,
            seed=args.seed,
        )
    else:
        raise SystemExit(f"unknown kind: {args.kind}")
    if args.output:
        Path(args.output).write_text(
            "\n".join(values) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(values)} values to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write("\n".join(values) + "\n")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    from colstats.io_jsonl import profile_to_dict
    from colstats.profile import collect_profile
    from colstats.schema import ColumnKind, HistogramKind

    values = [line for line in Path(args.input).read_text(encoding="utf-8").splitlines()]
    profile = collect_profile(
        name=args.name,
        values=values,
        kind=ColumnKind(args.kind),
        top_k_size=args.top_k,
        histogram_kind=HistogramKind(args.histogram),
        histogram_bins=args.bins,
    )
    payload = profile_to_dict(profile)
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote profile to {args.output}", file=sys.stderr)
    if args.show:
        print(f"column:           {profile.name}")
        print(f"kind:             {profile.kind.value}")
        print(f"n_rows:           {profile.n_rows}")
        print(f"n_non_null:       {profile.n_non_null}")
        print(f"null_fraction:    {profile.null_fraction * 100:.1f}%")
        print(
            f"cardinality:      {profile.cardinality}"
            f"{' (capped)' if profile.cardinality_capped else ''}"
        )
        if profile.numeric is not None:
            n = profile.numeric
            print(
                f"numeric:          min={n.min:.4g} max={n.max:.4g} "
                f"mean={n.mean:.4g} std={n.std:.4g}"
            )
            print(
                f"percentiles:      p25={n.p25:.4g} p50={n.p50:.4g} "
                f"p75={n.p75:.4g} p95={n.p95:.4g} p99={n.p99:.4g}"
            )
        if profile.strings is not None:
            s = profile.strings
            print(
                f"length:           min={s.min_length} max={s.max_length} "
                f"mean={s.mean_length:.2f}"
            )
        if profile.top_k:
            print("top_k:")
            for t in profile.top_k:
                print(f"  {t.value:<24} {t.count:>6}")
        if profile.histogram is not None:
            print(
                f"histogram:        {profile.histogram.kind.value} "
                f"({profile.histogram.n_bins} bins)"
            )
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    from dataclasses import replace

    from colstats.drift import ks, psi, psi_band
    from colstats.histogram import reproject
    from colstats.io_jsonl import load_profiles, profile_from_dict

    baseline_text = Path(args.baseline).read_text(encoding="utf-8")
    try:
        baseline_profile = profile_from_dict(json.loads(baseline_text))
    except json.JSONDecodeError:
        [baseline_profile] = load_profiles(baseline_text)

    if args.compared_values is not None:
        # Re-bin raw compared values into the baseline's histogram edges,
        # ensuring PSI / KS see aligned bins.
        if baseline_profile.histogram is None:
            raise SystemExit("baseline profile has no histogram")
        raw = [
            float(line)
            for line in Path(args.compared_values).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        reprojected = reproject(raw, baseline_profile.histogram)
        compared_profile = replace(
            baseline_profile,
            n_rows=len(raw),
            n_non_null=len(raw),
            histogram=reprojected,
        )
    else:
        compared_text = Path(args.compared).read_text(encoding="utf-8")
        try:
            compared_profile = profile_from_dict(json.loads(compared_text))
        except json.JSONDecodeError:
            [compared_profile] = load_profiles(compared_text)

    psi_score = psi(baseline_profile, compared_profile)
    ks_score = ks(baseline_profile, compared_profile)
    band = psi_band(psi_score)
    print(f"PSI: {psi_score:.4f}  ({band})")
    print(f"KS:  {ks_score:.4f}")
    return 0 if band == "stable" else 2


def cmd_summary(args: argparse.Namespace) -> int:
    """JSON roll-up of a profile (auto-generates from raw input)."""
    from colstats.io_jsonl import profile_to_dict
    from colstats.profile import collect_profile
    from colstats.schema import ColumnKind

    values = Path(args.input).read_text(encoding="utf-8").splitlines()
    profile = collect_profile(
        name=args.name,
        values=values,
        kind=ColumnKind(args.kind),
    )
    sys.stdout.write(
        json.dumps(profile_to_dict(profile), indent=2, ensure_ascii=False),
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="colstats",
        description="Single-pass column profiler — null pct, top-K, histograms, drift.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic column to stdout/file")
    sim.add_argument("--kind", choices=("NUMERIC", "CATEGORICAL", "STRING", "DATE"), required=True)
    sim.add_argument("--rows", type=int, default=1_000)
    sim.add_argument("--null-fraction", type=float, default=0.0)
    sim.add_argument("--shape", choices=("UNIFORM", "GAUSSIAN", "LOGNORMAL"), default="GAUSSIAN")
    sim.add_argument("--mean", type=float, default=0.0)
    sim.add_argument("--std", type=float, default=1.0)
    sim.add_argument("--categories", type=int, default=5)
    sim.add_argument("--skew", type=float, default=1.0)
    sim.add_argument("--length", type=int, default=10)
    sim.add_argument("--span-days", type=int, default=365)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    prof = sub.add_parser("profile", help="profile a column from a file (1 value/line)")
    prof.add_argument("--input", required=True)
    prof.add_argument("--name", default="col")
    prof.add_argument("--kind", choices=("NUMERIC", "CATEGORICAL", "STRING", "DATE"), required=True)
    prof.add_argument("--top-k", type=int, default=10)
    prof.add_argument(
        "--histogram", choices=("EQUI_WIDTH", "EQUI_DEPTH", "MAXDIFF"), default="EQUI_DEPTH"
    )
    prof.add_argument("--bins", type=int, default=10)
    prof.add_argument("--output", default=None, help="write profile JSON to this path")
    prof.add_argument("--show", action="store_true", help="print a summary to stdout")
    prof.set_defaults(func=cmd_profile)

    drift = sub.add_parser("drift", help="PSI + KS between two profile JSON files")
    drift.add_argument("--baseline", required=True)
    drift.add_argument("--compared", default=None, help="pre-computed compared profile JSON")
    drift.add_argument(
        "--compared-values",
        default=None,
        help="raw compared values, re-binned into baseline's bins",
    )
    drift.set_defaults(func=cmd_drift)

    summ = sub.add_parser("summary", help="profile + emit JSON to stdout")
    summ.add_argument("--input", required=True)
    summ.add_argument("--name", default="col")
    summ.add_argument("--kind", choices=("NUMERIC", "CATEGORICAL", "STRING", "DATE"), required=True)
    summ.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
