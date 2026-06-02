"""``dbtlin`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from dbtlin import __version__

    print(f"dbt-model-lineage-graph {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from dbtlin.io_jsonl import project_to_json
    from dbtlin.simulator import generate

    project = generate(seed=args.seed, inject_cycle=args.cycle)
    out_text = project_to_json(project)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote project with {len(project)} models to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out_text)
        sys.stdout.write("\n")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from dbtlin.io_jsonl import dump_models, project_from_json
    from dbtlin.parser import parse_project

    project = project_from_json(Path(args.input).read_text(encoding="utf-8"))
    models = parse_project(project)
    out_text = dump_models(models)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(models)} parsed models to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out_text)
    return 0


def _build_graph_from_input(input_path: str):  # type: ignore[no-untyped-def]
    """Either a project JSON file or an already-parsed models JSONL file."""
    from dbtlin.graph import build_graph
    from dbtlin.io_jsonl import load_models, project_from_json
    from dbtlin.parser import parse_project

    text = Path(input_path).read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        project = project_from_json(text)
        models = parse_project(project)
    else:
        models = load_models(text)
    return build_graph(models), models


def cmd_graph(args: argparse.Namespace) -> int:
    from dbtlin.graph import leaves, roots
    from dbtlin.io_jsonl import dump_edges

    graph, _ = _build_graph_from_input(args.input)
    edges = graph.edges()
    if args.output:
        Path(args.output).write_text(dump_edges(edges), encoding="utf-8")
        print(f"wrote {len(edges)} edges to {args.output}", file=sys.stderr)
    print(f"{len(graph.nodes)} nodes, {len(edges)} edges")
    print(f"\nRoots ({len(roots(graph))}):")
    for r in roots(graph)[: args.show]:
        print(f"  {r.label}")
    print(f"\nLeaves ({len(leaves(graph))}):")
    for ll in leaves(graph)[: args.show]:
        print(f"  {ll.label}")
    return 0


def cmd_cycles(args: argparse.Namespace) -> int:
    from dbtlin.graph import find_cycles

    graph, _ = _build_graph_from_input(args.input)
    cycles = find_cycles(graph)
    print(f"Cycles found: {len(cycles)}")
    for c in cycles:
        names = " → ".join(n.label for n in c.cycle)
        print(f"  {names}")
    return 0 if not cycles else 2


def cmd_topo(args: argparse.Namespace) -> int:
    from dbtlin.graph import topological_order

    graph, _ = _build_graph_from_input(args.input)
    try:
        order = topological_order(graph)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    for n in order:
        print(n.label)
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    from dbtlin.impact import impact_by_name
    from dbtlin.schema import NodeId, NodeKind

    graph, _ = _build_graph_from_input(args.input)
    if args.source:
        target = NodeId(kind=NodeKind.SOURCE, name=args.target)
        from dbtlin.impact import impact as _impact

        report = _impact(graph, target)
    else:
        report = impact_by_name(graph, args.target)
    print(f"Target: {report.target.label}")
    print(f"\nUpstream ({len(report.upstream)}):")
    for u in report.upstream[: args.show]:
        print(f"  {u.label}")
    print(f"\nDownstream ({len(report.downstream)}):")
    for d in report.downstream[: args.show]:
        print(f"  {d.label}")
    print(f"\nTotal affected: {report.n_total_affected}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from dbtlin.graph import find_cycles, leaves, roots
    from dbtlin.schema import NodeKind

    graph, _ = _build_graph_from_input(args.input)
    n_model_nodes = sum(1 for n in graph.nodes if n.kind is NodeKind.MODEL)
    n_source_nodes = sum(1 for n in graph.nodes if n.kind is NodeKind.SOURCE)
    payload = {
        "n_nodes": len(graph.nodes),
        "n_models": n_model_nodes,
        "n_sources": n_source_nodes,
        "n_edges": sum(len(s) for s in graph.upstream_of.values()),
        "n_roots": len(roots(graph)),
        "n_leaves": len(leaves(graph)),
        "n_cycles": len(find_cycles(graph)),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="dbtlin",
        description="dbt SQL → lineage DAG → cycles + impact analysis.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic dbt project")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--cycle", action="store_true", help="inject a deliberate cycle for testing")
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    pa = sub.add_parser("parse", help="parse a project JSON into Model records")
    pa.add_argument("--input", required=True)
    pa.add_argument("--output", default=None)
    pa.set_defaults(func=cmd_parse)

    gr = sub.add_parser("graph", help="build graph + show roots/leaves")
    gr.add_argument("--input", required=True)
    gr.add_argument("--output", default=None, help="emit edges JSONL")
    gr.add_argument("--show", type=int, default=20)
    gr.set_defaults(func=cmd_graph)

    cy = sub.add_parser("cycles", help="detect cycles (Tarjan SCC)")
    cy.add_argument("--input", required=True)
    cy.set_defaults(func=cmd_cycles)

    to = sub.add_parser("topo", help="topological sort (Kahn)")
    to.add_argument("--input", required=True)
    to.set_defaults(func=cmd_topo)

    im = sub.add_parser("impact", help="upstream + downstream impact of a node")
    im.add_argument("--input", required=True)
    im.add_argument("--target", required=True, help="model name")
    im.add_argument(
        "--source", action="store_true", help="target is a SOURCE (schema.table) not a MODEL"
    )
    im.add_argument("--show", type=int, default=20)
    im.set_defaults(func=cmd_impact)

    sm = sub.add_parser("summary", help="JSON roll-up of graph stats")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
