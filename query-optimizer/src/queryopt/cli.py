"""
CLI for the query optimizer.

Subcommands
-----------
  optimize   Read a JSONL query spec and emit an optimized plan as JSONL.
  demo       Run the built-in 10-table star-schema demo.
  explain    Pretty-print a plan produced by `optimize`.

JSONL query spec format (one object per line)::

    {"tables": ["orders", "customer"], "predicates": [
        {"left_table": "orders", "left_col": "cid",
         "right_table": "customer", "right_col": "cid"}
    ], "row_counts": {"orders": 500000, "customer": 100000}}

JSONL plan output::

    {"join_order": [...], "total_cost": 1234.5,
     "algorithm": "HashJoin", "io_cost": 1200.0, "cpu_cost": 34.5}
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import TYPE_CHECKING, Any

from queryopt.cascades import CascadesOptimizer
from queryopt.cost_model import CostModel
from queryopt.expressions import PhysicalJoin, PhysicalScan, Predicate
from queryopt.histogram import ColumnStats, StatsCatalog, TableStats
from queryopt.schema import build_star_schema

if TYPE_CHECKING:
    from queryopt.memo import Winner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_catalog_from_spec(
    spec: dict[str, Any],
) -> tuple[StatsCatalog, list[str], list[Predicate]]:
    """Build a StatsCatalog from a JSONL query spec dict."""
    tables: list[str] = spec["tables"]
    row_counts: dict[str, int] = spec.get("row_counts", {})
    pred_dicts: list[dict[str, str]] = spec.get("predicates", [])

    catalog = StatsCatalog()
    for t in tables:
        nrows = row_counts.get(t, 1000)
        ts = TableStats(t, row_count=nrows)
        # Synthesise a generic key column so selectivity estimates work
        ts.add_column(ColumnStats(f"{t}_id", num_distinct=nrows))
        catalog.register(ts)

    predicates = [
        Predicate(
            left_table=p["left_table"],
            left_col=p["left_col"],
            right_table=p["right_table"],
            right_col=p["right_col"],
        )
        for p in pred_dicts
    ]
    return catalog, tables, predicates


def _winner_to_dict(winner: Winner) -> dict[str, Any]:
    """Serialise a Winner tree into a JSON-able dict."""
    expr = winner.expr
    node: dict[str, Any] = {
        "cost": winner.cost.total,
        "io_cost": winner.cost.io_cost,
        "cpu_cost": winner.cost.cpu_cost,
    }
    if isinstance(expr, PhysicalScan):
        node["op"] = "SeqScan"
        node["table"] = expr.table
    elif isinstance(expr, PhysicalJoin):
        node["op"] = expr.algorithm.value
        node["children"] = [_winner_to_dict(cw) for cw in winner.child_winners.values()]
    return node


def _join_sequence(winner: Winner) -> list[str]:
    order: list[str] = []
    _collect(winner, order)
    return order


def _collect(winner: Winner, result: list[str]) -> None:
    expr = winner.expr
    if isinstance(expr, PhysicalScan):
        result.append(expr.table)
        return
    if isinstance(expr, PhysicalJoin):
        for cid in [expr.left_group, expr.right_group]:
            if cid in winner.child_winners:
                _collect(winner.child_winners[cid], result)


def _plan_lines(winner: Winner, depth: int = 0) -> list[str]:
    """Render the winning plan as an indented tree."""
    pad = "  " * depth
    expr = winner.expr
    cost_str = (
        f"total={winner.cost.total:>12,.1f}"
        f"  io={winner.cost.io_cost:>10,.1f}"
        f"  cpu={winner.cost.cpu_cost:>8.2f}"
    )
    lines = [f"{pad}{expr}   [{cost_str}]"]
    if isinstance(expr, PhysicalJoin):
        for cid in [expr.left_group, expr.right_group]:
            if cid in winner.child_winners:
                lines.extend(_plan_lines(winner.child_winners[cid], depth + 1))
    return lines


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_optimize(args: argparse.Namespace) -> int:
    """Read JSONL from stdin (or a file), write plan JSONL to stdout."""
    src = open(args.input) if args.input else sys.stdin  # noqa: SIM115
    try:
        for raw_line in src:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            spec: dict[str, Any] = json.loads(raw_line)
            catalog, tables, predicates = _build_catalog_from_spec(spec)
            cost_model = CostModel(
                avg_row_bytes={
                    t: (_ts.avg_row_bytes if (_ts := catalog.get(t)) is not None else 100)
                    for t in tables
                }
            )
            opt = CascadesOptimizer(catalog, cost_model)
            winner = opt.optimize(tables, predicates)
            out: dict[str, Any] = {
                "join_order": _join_sequence(winner),
                "total_cost": winner.cost.total,
                "io_cost": winner.cost.io_cost,
                "cpu_cost": winner.cost.cpu_cost,
                "algorithm": (
                    winner.expr.algorithm.value
                    if isinstance(winner.expr, PhysicalJoin)
                    else "SeqScan"
                ),
                "plan": _winner_to_dict(winner),
            }
            print(json.dumps(out))
    finally:
        if args.input:
            src.close()
    return 0


def cmd_demo(_args: argparse.Namespace) -> int:
    """Run the built-in 10-table star-schema demo."""
    print("=" * 72)
    print("  Cascades Cost-Based Query Optimizer - 10-Table Star Schema")
    print("=" * 72)

    catalog, tables, predicates = build_star_schema()

    print(f"\nRelations ({len(tables)}):")
    for t in tables:
        ts = catalog.get(t)
        if ts:
            print(f"  {t:<22}  {ts.row_count:>12,} rows  {ts.avg_row_bytes} B/row")

    print(f"\nJoin predicates ({len(predicates)}):")
    for p in predicates:
        print(f"  {p}")

    cost_model = CostModel(
        avg_row_bytes={
            t: (_ts.avg_row_bytes if (_ts := catalog.get(t)) is not None else 100) for t in tables
        }
    )
    optimizer = CascadesOptimizer(catalog, cost_model)

    print("\nOptimizing ...", end=" ", flush=True)
    t0 = time.perf_counter()
    winner = optimizer.optimize(tables, predicates)
    elapsed = time.perf_counter() - t0
    print(f"done in {elapsed * 1000:.1f} ms  ({optimizer._calls} DP states explored)")

    order = _join_sequence(winner)
    print("\n" + "-" * 72)
    print("OPTIMAL JOIN ORDER")
    print("-" * 72)
    print(" ⋈  ".join(order))

    print("\n" + "-" * 72)
    print("PHYSICAL PLAN TREE")
    print("-" * 72)
    for line in _plan_lines(winner):
        print(line)

    print(f"\nTotal plan cost: {winner.cost.total:,.2f} units")

    print("\n" + "-" * 72)
    print("INTERMEDIATE RESULT CARDINALITIES")
    print("-" * 72)
    print(f"  {'Tables in group':<42} {'Est. rows':>14}")
    print(f"  {'-' * 42} {'-' * 14}")
    for g in sorted(optimizer.memo.all_groups(), key=lambda x: len(x.tables)):
        if len(g.tables) < 2:
            continue
        label = str(sorted(g.tables))
        if len(label) > 40:
            label = label[:37] + "...]"
        print(f"  {label:<42} {g.stats.row_count:>14,.0f}")

    print("\n" + "=" * 72)
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Pretty-print a JSONL plan produced by `optimize`."""
    src = open(args.input) if args.input else sys.stdin  # noqa: SIM115
    try:
        for raw_line in src:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            plan: dict[str, Any] = json.loads(raw_line)
            join_order = plan.get("join_order", [])
            total_cost = plan.get("total_cost", 0.0)
            algo = plan.get("algorithm", "unknown")
            print(f"Join order : {' -> '.join(join_order)}")
            print(f"Algorithm  : {algo}")
            print(f"Total cost : {total_cost:,.2f}")
            print()
    finally:
        if args.input:
            src.close()
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="queryopt",
        description="Cascades cost-based query optimizer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # optimize
    p_opt = sub.add_parser("optimize", help="Optimize a JSONL query spec")
    p_opt.add_argument(
        "-i", "--input", metavar="FILE", default="", help="Input JSONL file (default: stdin)"
    )
    p_opt.set_defaults(func=cmd_optimize)

    # demo
    p_demo = sub.add_parser("demo", help="Run the built-in star-schema demo")
    p_demo.set_defaults(func=cmd_demo)

    # explain
    p_exp = sub.add_parser("explain", help="Pretty-print a JSONL plan")
    p_exp.add_argument(
        "-i", "--input", metavar="FILE", default="", help="Input JSONL file (default: stdin)"
    )
    p_exp.set_defaults(func=cmd_explain)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code: int = args.func(args)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
