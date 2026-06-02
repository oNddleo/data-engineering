"""``cicscore`` command-line interface."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from cicscore import __version__

    print(f"credit-scoring-pipeline-vn {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from cicscore.io_jsonl import dump_borrowers
    from cicscore.simulator import generate

    obs = date.fromisoformat(args.observation_date) if args.observation_date else None
    borrowers = generate(
        n_borrowers=args.borrowers,
        seed=args.seed,
        observation_date=obs,
    )
    out = dump_borrowers(borrowers)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(borrowers)} borrowers to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    from cicscore.features import extract
    from cicscore.io_jsonl import dump_features, load_borrowers

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    obs_date = date.fromisoformat(args.observation_date)
    features = [extract(b, obs_date) for b in load_borrowers(text)]
    out = dump_features(features)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(features)} feature rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from cicscore.features import extract
    from cicscore.io_jsonl import dump_scores, load_borrowers
    from cicscore.scoring import baseline_score

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    obs_date = date.fromisoformat(args.observation_date)
    scores = [baseline_score(extract(b, obs_date)) for b in load_borrowers(text)]
    out = dump_scores(scores)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(scores)} scores to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    from cicscore.features import extract
    from cicscore.io_jsonl import load_borrowers
    from cicscore.scoring import baseline_score

    text = (
        sys.stdin.read()
        if args.input in (None, "-")
        else Path(args.input).read_text(encoding="utf-8")
    )
    obs_date = date.fromisoformat(args.observation_date)
    target = args.borrower_id
    for b in load_borrowers(text):
        if b.borrower_id == target:
            f = extract(b, obs_date)
            s = baseline_score(f)
            print(f"=== {b.borrower_id} @ {obs_date.isoformat()} ===")
            print(f"score = {s.score}")
            print(f"current_max_group       = {f.current_max_group}")
            print(f"worst_group_ever        = {f.worst_group_ever}")
            print(f"max_group_24m           = {f.max_group_24m}")
            print(f"months_in_group_2plus_24m = {f.months_in_group_2plus_24m}")
            print(f"active_contracts        = {f.active_contracts}")
            print(f"unique_lenders          = {f.unique_lenders}")
            print(f"total_outstanding_vnd   = {f.total_outstanding_principal_vnd:,}")
            print(f"provision_estimate_vnd  = {f.provision_estimate_vnd:,}")
            print(f"months_since_first_credit = {f.months_since_first_credit}")
            print(f"inquiries_6m            = {f.inquiries_6m}")
            print(
                f"dti_ratio               = "
                f"{'n/a' if f.dti_ratio is None else format(f.dti_ratio, '.2f')}"
            )
            if s.reasons:
                print("\nScore breakdown:")
                for r in s.reasons:
                    print(f"  {r.delta:>+5d}  {r.label}")
            else:
                print("\nNo penalties / bonuses applied.")
            return 0
    print(f"borrower_id={target!r} not found", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cicscore",
        description="Feature-engineering + baseline credit scoring on Vietnamese CIC data.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic CIC borrowers as JSONL")
    sim.add_argument("--borrowers", type=int, default=10)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--observation-date", dest="observation_date", default=None)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ex = sub.add_parser("extract", help="extract feature vectors from borrowers JSONL")
    ex.add_argument("--input", default=None)
    ex.add_argument("--observation-date", dest="observation_date", required=True)
    ex.add_argument("--output", default=None)
    ex.set_defaults(func=cmd_extract)

    sc = sub.add_parser("score", help="extract + score in one pass")
    sc.add_argument("--input", default=None)
    sc.add_argument("--observation-date", dest="observation_date", required=True)
    sc.add_argument("--output", default=None)
    sc.set_defaults(func=cmd_score)

    insp = sub.add_parser("inspect", help="dump features + score for one borrower")
    insp.add_argument("--input", required=True)
    insp.add_argument("--observation-date", dest="observation_date", required=True)
    insp.add_argument("--borrower-id", dest="borrower_id", required=True)
    insp.set_defaults(func=cmd_inspect)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
