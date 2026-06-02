"""``bhyt`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from bhyt import __version__

    print(f"healthcare-claims-processor {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from bhyt.io_jsonl import dump_cards, dump_claims, dump_patients
    from bhyt.simulator import generate

    patients, cards, claims = generate(
        n_patients=args.patients,
        n_claims=args.claims,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "patients.jsonl").write_text(dump_patients(patients), encoding="utf-8")
    (out_dir / "cards.jsonl").write_text(dump_cards(cards), encoding="utf-8")
    (out_dir / "claims.jsonl").write_text(dump_claims(claims), encoding="utf-8")
    print(
        f"wrote {len(patients)} patients + {len(cards)} cards + {len(claims)} claims",
        file=sys.stderr,
    )
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    """Decode a BHYT card number → scheme + priority + category."""
    from bhyt.card import decode_prefix, is_valid_format, normalise

    raw = normalise(args.card_number)
    if not is_valid_format(raw):
        print(f"❌ {raw}: invalid format", file=sys.stderr)
        return 1
    info = decode_prefix(raw)
    payload = {
        "card_number": raw,
        "scheme_letter": info.scheme_letter,
        "scheme_name": info.scheme_name,
        "priority_letter": info.priority_letter,
        "category": info.category.value,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_icd(args: argparse.Namespace) -> int:
    """Lookup an ICD-10-VN code."""
    from bhyt.icd10vn import lookup

    entry = lookup(args.code)
    if entry is None:
        print(f"❌ {args.code}: not in bundled ICD-10-VN subset", file=sys.stderr)
        return 1
    sys.stdout.write(
        json.dumps(
            {
                "code": entry.code,
                "name_vi": entry.name_vi,
                "name_en": entry.name_en,
                "chapter": entry.chapter,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    sys.stdout.write("\n")
    return 0


def cmd_calc(args: argparse.Namespace) -> int:
    from bhyt.calculator import calculate
    from bhyt.io_jsonl import dump_reimbursements, load_claims

    claims = load_claims(Path(args.input).read_text(encoding="utf-8"))
    results = [calculate(c, emergency=args.emergency) for c in claims]
    if args.output:
        Path(args.output).write_text(dump_reimbursements(results), encoding="utf-8")
        print(f"wrote {len(results)} reimbursements to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'claim':<14} {'subtotal':>12} {'cov%':>6} {'pen%':>6} "
            f"{'insurer':>12} {'patient':>10} notes"
        )
        for r in results[: args.show]:
            cov_pct = r.coverage_rate_bps / 100
            pen_pct = r.referral_penalty_bps / 100
            print(
                f"{r.claim_id:<14} {r.subtotal_vnd:>12,} "
                f"{cov_pct:>5.1f}% {pen_pct:>5.1f}% "
                f"{r.insurer_pays_vnd:>12,} {r.patient_pays_vnd:>10,} "
                f"{('!' if r.notes else '')}"
            )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from bhyt.calculator import calculate
    from bhyt.io_jsonl import load_claims

    claims = load_claims(Path(args.input).read_text(encoding="utf-8"))
    results = [calculate(c) for c in claims]
    insurer_total = sum(r.insurer_pays_vnd for r in results)
    patient_total = sum(r.patient_pays_vnd for r in results)
    subtotal_total = sum(r.subtotal_vnd for r in results)
    n_with_notes = sum(1 for r in results if r.notes)
    by_category: dict[str, int] = {}
    by_care_level: dict[str, int] = {}
    for c in claims:
        from bhyt.card import decode_prefix, is_valid_format

        if is_valid_format(c.card_number):
            cat = decode_prefix(c.card_number).category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        by_care_level[c.care_level.value] = by_care_level.get(c.care_level.value, 0) + 1
    payload = {
        "n_claims": len(claims),
        "subtotal_vnd_total": subtotal_total,
        "insurer_pays_vnd_total": insurer_total,
        "patient_pays_vnd_total": patient_total,
        "share_paid_by_insurer_pct": round(insurer_total / subtotal_total * 100, 1)
        if subtotal_total
        else 0.0,
        "n_with_notes": n_with_notes,
        "by_category": dict(sorted(by_category.items())),
        "by_care_level": dict(sorted(by_care_level.items())),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="bhyt",
        description="VN BHYT claims processor — cards, ICD-10-VN, coverage, reimbursement.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="generate patients + cards + claims")
    sim.add_argument("--patients", type=int, default=30)
    sim.add_argument("--claims", type=int, default=60)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    dc = sub.add_parser("decode", help="decode a BHYT card number")
    dc.add_argument("card_number")
    dc.set_defaults(func=cmd_decode)

    icd = sub.add_parser("icd", help="look up an ICD-10-VN code")
    icd.add_argument("code")
    icd.set_defaults(func=cmd_icd)

    cl = sub.add_parser("calc", help="compute reimbursements for a claims JSONL file")
    cl.add_argument("--input", required=True)
    cl.add_argument("--output", default=None)
    cl.add_argument(
        "--emergency",
        action="store_true",
        help="treat all claims as emergencies (waive referral penalty)",
    )
    cl.add_argument("--show", type=int, default=0)
    cl.set_defaults(func=cmd_calc)

    sm = sub.add_parser("summary", help="JSON roll-up of payouts + categories")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
