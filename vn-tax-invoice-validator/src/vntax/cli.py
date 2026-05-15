"""``vntax`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vntax import __version__

    print(f"vn-tax-invoice-validator {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vntax.io_jsonl import dump_invoices
    from vntax.simulator import generate

    invoices = generate(
        n_invoices=args.n,
        bad_fraction=args.bad_fraction,
        seed=args.seed,
    )
    out = dump_invoices(invoices)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(invoices)} invoices to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from vntax.io_jsonl import dump_findings, load_invoices
    from vntax.validator import has_errors, validate

    invoices = list(load_invoices(Path(args.input).read_text(encoding="utf-8")))
    all_findings = []
    n_with_errors = 0
    for inv in invoices:
        fs = validate(inv)
        all_findings.extend(fs)
        if has_errors(fs):
            n_with_errors += 1
    if args.output:
        Path(args.output).write_text(dump_findings(all_findings), encoding="utf-8")
        print(
            f"wrote {len(all_findings)} findings ({n_with_errors}/{len(invoices)} "
            f"invoices have errors) to {args.output}",
            file=sys.stderr,
        )
    if args.show:
        print(f"{'invoice':<14} {'sev':<8} {'code':<28} detail")
        for f in all_findings[: args.show]:
            print(f"{f.invoice_id:<14} {f.severity.value:<8} {f.code:<28} {f.detail}")
    if args.summary:
        print(
            f"\nSummary: {n_with_errors}/{len(invoices)} invoices have ≥1 ERROR "
            f"({len(all_findings)} total findings)"
        )
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    from vntax.registry import InMemoryRegistry
    from vntax.taxcode import is_valid, normalise

    registry = InMemoryRegistry()
    norm = normalise(args.mst)
    if not is_valid(norm):
        print(f"❌ {norm}: checksum FAILED", file=sys.stderr)
        return 1
    hit = registry.lookup(norm)
    if hit is None:
        print(f"✓ {norm}: checksum OK, but not in registry")
        return 2
    payload = {
        "mst": hit.mst,
        "name": hit.name,
        "address": hit.address,
        "status": hit.status,
        "registered_at": hit.registered_at,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from vntax.io_jsonl import load_invoices
    from vntax.validator import Severity, validate

    invoices = list(load_invoices(Path(args.input).read_text(encoding="utf-8")))
    code_counts: Counter[str] = Counter()
    sev_counts: Counter[str] = Counter()
    n_with_errors = 0
    for inv in invoices:
        fs = validate(inv)
        if any(f.severity is Severity.ERROR for f in fs):
            n_with_errors += 1
        for f in fs:
            code_counts[f.code] += 1
            sev_counts[f.severity.value] += 1
    payload = {
        "n_invoices": len(invoices),
        "n_with_errors": n_with_errors,
        "by_severity": dict(sev_counts),
        "by_code": dict(code_counts.most_common()),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vntax",
        description="Vietnamese e-invoice (hóa đơn điện tử) validator — Nghị định 123 + Thông tư 78.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="generate a mix of valid + intentionally-bad invoices")
    sim.add_argument("--n", type=int, default=100)
    sim.add_argument("--bad-fraction", type=float, default=0.20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    val = sub.add_parser("validate", help="run all checks over a JSONL invoice file")
    val.add_argument("--input", required=True)
    val.add_argument("--output", default=None)
    val.add_argument("--show", type=int, default=0, help="print first N findings to stdout")
    val.add_argument("--summary", action="store_true", help="print one-line summary at end")
    val.set_defaults(func=cmd_validate)

    lk = sub.add_parser("lookup", help="check an MST checksum + look up in the bundled registry")
    lk.add_argument("mst")
    lk.set_defaults(func=cmd_lookup)

    sm = sub.add_parser("summary", help="JSON summary of validation across the file")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
