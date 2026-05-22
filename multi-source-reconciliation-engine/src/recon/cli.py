"""CLI for multi-source reconciliation engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_reconcile(args: argparse.Namespace) -> int:
    from recon.engine import reconcile
    from recon.io_jsonl import load_transactions, report_to_jsonl
    from recon.schema import Transaction  # noqa: TCH001

    sources_dir = Path(args.sources_dir)
    all_sources: dict[str, list[Transaction]] = {}
    for jsonl_file in sorted(sources_dir.glob("*.jsonl")):
        src_name = jsonl_file.stem
        all_sources[src_name] = load_transactions(jsonl_file)

    if not all_sources:
        print(f"No .jsonl files found in {sources_dir}", file=sys.stderr)
        return 1

    report = reconcile(all_sources, ref_threshold=args.ref_threshold)
    report_to_jsonl(report, sys.stdout)
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    from recon.io_jsonl import dump_transactions
    from recon.simulator import generate_sources

    sources = generate_sources(
        n_transactions=args.n,
        seed=args.seed,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, txns in sources.items():
        dump_transactions(txns, out / f"{name}.jsonl")
    print(json.dumps({"sources": list(sources.keys()), "output_dir": str(out)}))
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    from recon.io_jsonl import report_from_jsonl

    with open(args.report) as fh:
        report = report_from_jsonl(fh)

    summary = {
        "run_date": report.run_date.isoformat(),
        "sources": report.sources,
        "total_records": report.total_records,
        "matched": report.matched,
        "discrepancies": report.discrepancies,
        "match_rate": f"{report.match_rate:.1%}",
    }
    print(json.dumps(summary, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="recon",
        description="Multi-source financial reconciliation engine",
    )
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("reconcile", help="Reconcile sources in a directory")
    rec.add_argument("sources_dir", help="Directory with per-source .jsonl files")
    rec.add_argument("--ref-threshold", type=float, default=0.85)

    sim = sub.add_parser("simulate", help="Generate synthetic transaction data")
    sim.add_argument("-n", type=int, default=100, help="Number of base transactions")
    sim.add_argument("--output-dir", default="sim_data")
    sim.add_argument("--seed", type=int, default=42)

    summ = sub.add_parser("summary", help="Summarise a reconciliation report")
    summ.add_argument("report", help="Path to JSONL report file")

    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "reconcile": _cmd_reconcile,
        "simulate": _cmd_simulate,
        "summary": _cmd_summary,
    }
    code = dispatch[args.command](args)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
