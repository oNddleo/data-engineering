"""CLI entry point for ivm-engine.

Subcommands
-----------
  ivm demo        Run the built-in GROUP BY demo.
  ivm snapshot    Read a JSONL update stream and write a snapshot.
  ivm version     Print the package version.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import ivm
from ivm.engine import IVMEngine
from ivm.io.jsonl import dump_snapshot, read_jsonl_updates


def _cmd_version(args: argparse.Namespace) -> int:  # noqa: ARG001
    print(f"ivm-engine {ivm.__version__}")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Run a self-contained GROUP BY demo."""
    import ivm.aggregates as agg

    engine = IVMEngine()
    orders = engine.source("orders")
    view = orders.group_by(
        ["category"],
        {
            "total_revenue": agg.Sum("amount"),
            "order_count": agg.Count(),
        },
    )
    engine.register_view("summary", view)

    batch = [
        {"category": "books",       "amount": 25},
        {"category": "electronics", "amount": 299},
        {"category": "books",       "amount": 18},
        {"category": "clothing",    "amount": 75},
        {"category": "electronics", "amount": 149},
    ]
    for rec in batch:
        engine.ingest("orders", rec, timestamp=1000)

    print("Category summary (after initial batch):")
    for row in sorted(engine.query("summary"), key=lambda r: r["category"]):
        print(f"  {row['category']:12s}  revenue={row['total_revenue']}  "
              f"count={row['order_count']}")

    # Retract one record
    engine.retract("orders", {"category": "books", "amount": 18}, timestamp=2000)

    print("\nCategory summary (after retracting books/$18):")
    for row in sorted(engine.query("summary"), key=lambda r: r["category"]):
        print(f"  {row['category']:12s}  revenue={row['total_revenue']}  "
              f"count={row['order_count']}")
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    """Replay a JSONL update stream through a source and write a snapshot."""
    updates = read_jsonl_updates(args.input)
    if not updates:
        print("No updates found in input file.", file=sys.stderr)
        return 1

    engine = IVMEngine()
    src = engine.source("stream")
    engine.register_view("out", src)

    for u in updates:
        engine.ingest("stream", u.record, diff=u.diff, timestamp=u.timestamp)

    records = engine.query("out")
    n = dump_snapshot(records, args.output)
    print(f"Wrote {n} records to {args.output}")
    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ivm",
        description="Incremental View Maintenance engine CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Print package version")
    sub.add_parser("demo", help="Run the built-in GROUP BY demo")

    snap_p = sub.add_parser("snapshot", help="Replay update stream and write snapshot")
    snap_p.add_argument("input", help="Input JSONL update stream file")
    snap_p.add_argument("output", help="Output JSONL snapshot file")

    args = parser.parse_args()

    dispatch = {
        "version": _cmd_version,
        "demo": _cmd_demo,
        "snapshot": _cmd_snapshot,
    }
    fn = dispatch[args.command]
    code = fn(args)
    if code:
        sys.exit(code)
