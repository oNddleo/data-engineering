"""CLI for intelligent compaction engine."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_plan(args: argparse.Namespace) -> int:
    from compact.engine import plan
    from compact.io_jsonl import load_tablemeta, plan_to_jsonl

    with open(args.table_meta) as fh:
        table = load_tablemeta(fh)

    patterns = None
    if args.patterns:
        from compact.schema import QueryPattern

        with open(args.patterns) as fh:
            raw = json.load(fh)
        patterns = [
            QueryPattern(
                query_id=str(p.get("query_id", "")),
                filter_columns=list(p.get("filter_columns", [])),
                join_columns=list(p.get("join_columns", [])),
                group_by_columns=list(p.get("group_by_columns", [])),
                frequency=int(p.get("frequency", 1)),
            )
            for p in raw
        ]

    result = plan(
        table,
        query_patterns=patterns,
        prune_after_days=args.prune_after_days,
    )
    plan_to_jsonl(result, sys.stdout)
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    from pathlib import Path

    from compact.io_jsonl import dump_tablemeta
    from compact.simulator import generate_query_patterns, generate_table

    table = generate_table(
        n_partitions=args.partitions,
        seed=args.seed,
        table_name=args.table_name,
    )
    patterns = generate_query_patterns(n_patterns=args.patterns, seed=args.seed)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "table_meta.json", "w") as fh:
        dump_tablemeta(table, fh)
    with open(out / "query_patterns.json", "w") as fh:
        json.dump(
            [
                {
                    "query_id": p.query_id,
                    "filter_columns": p.filter_columns,
                    "join_columns": p.join_columns,
                    "group_by_columns": p.group_by_columns,
                    "frequency": p.frequency,
                }
                for p in patterns
            ],
            fh,
            indent=2,
        )
    print(
        json.dumps(
            {
                "table_name": table.table_name,
                "partitions": len(table.partitions),
                "total_files": table.total_files,
                "output_dir": str(out),
            }
        )
    )
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    from compact.io_jsonl import plan_from_jsonl

    with open(args.plan) as fh:
        cplan = plan_from_jsonl(fh)

    print(
        json.dumps(
            {
                "table_name": cplan.table_name,
                "task_count": len(cplan.tasks),
                "action_counts": cplan.action_counts,
                "estimated_file_reduction": cplan.estimated_file_reduction,
                "estimated_size_reduction_mb": round(cplan.estimated_size_reduction_bytes / 1e6, 2),
            },
            indent=2,
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compact",
        description="Intelligent compaction engine for lakehouse tables",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("plan", help="Generate a compaction plan")
    pl.add_argument("table_meta", help="Path to table metadata JSON")
    pl.add_argument("--patterns", help="Path to query patterns JSON")
    pl.add_argument("--prune-after-days", type=int, default=90)

    sim = sub.add_parser("simulate", help="Generate synthetic table data")
    sim.add_argument("--partitions", type=int, default=20)
    sim.add_argument("--patterns", type=int, default=50, dest="patterns")
    sim.add_argument("--seed", type=int, default=42)
    sim.add_argument("--table-name", default="events")
    sim.add_argument("--output-dir", default="sim_data")

    summ = sub.add_parser("summary", help="Summarise a compaction plan")
    summ.add_argument("plan", help="Path to compaction plan JSONL")

    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "plan": _cmd_plan,
        "simulate": _cmd_simulate,
        "summary": _cmd_summary,
    }
    code = dispatch[args.command](args)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
