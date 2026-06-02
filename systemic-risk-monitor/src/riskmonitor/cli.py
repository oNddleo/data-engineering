"""CLI entry point for riskmonitor.

Subcommands
-----------
simulate    Generate synthetic interbank transfers and optionally write to file.
analyze     Load transfers from JSON and produce a RiskReport.
report      Load transfers from JSON, analyze, and emit a formatted report.
"""

from __future__ import annotations

import argparse
import json
import sys

from .alerts import AlertEngine
from .analyzer import RiskAnalyzer
from .graph import ExposureGraph
from .simulator import TransactionSimulator, Transfer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_graph(transfers_data: list[dict[str, object]]) -> ExposureGraph:
    graph = ExposureGraph()
    for t in transfers_data:
        graph.add_transfer(str(t["from_id"]), str(t["to_id"]), float(t["amount"]))  # type: ignore[arg-type]
    return graph


def _transfers_to_dicts(transfers: list[Transfer]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for t in transfers:
        result.append({"from_id": t.from_id, "to_id": t.to_id, "amount": t.amount})
    return result


# ---------------------------------------------------------------------------
# Subcommand: simulate
# ---------------------------------------------------------------------------


def _cmd_simulate(args: argparse.Namespace) -> None:
    sim = TransactionSimulator(seed=args.seed)
    transfers = sim.generate(n=args.n, seed=args.seed)
    data = _transfers_to_dicts(transfers)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        print(f"Wrote {len(data)} transfers to {args.output}", file=sys.stderr)
    else:
        json.dump(data, sys.stdout, indent=2)
        print()


# ---------------------------------------------------------------------------
# Subcommand: analyze
# ---------------------------------------------------------------------------


def _cmd_analyze(args: argparse.Namespace) -> None:
    with open(args.input, encoding="utf-8") as fh:
        transfers_data: list[dict[str, object]] = json.load(fh)

    graph = _build_graph(transfers_data)
    report = RiskAnalyzer().analyze(graph)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        print()


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------


def _format_text(report_dict: dict[str, object], alerts: list[dict[str, object]]) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  SYSTEMIC RISK MONITOR — RISK REPORT")
    lines.append("=" * 60)

    lines.append("\n[ Concentration Metrics ]")
    lines.append(f"  HHI  : {report_dict['hhi']:.4f}")
    lines.append(f"  Gini : {report_dict['gini']:.4f}")

    lines.append("\n[ Cycle Risk ]")
    cycles = report_dict.get("cycles", [])
    assert isinstance(cycles, list)
    lines.append(f"  Cycles detected : {len(cycles)}")
    if cycles:
        lines.append(f"  Max notional    : {report_dict['max_cycle_notional']:,.0f}")

    lines.append("\n[ Centrality ]")
    lines.append(f"  Betweenness max : {report_dict['betweenness_max']:.4f}")
    lines.append(f"  Max node        : {report_dict['betweenness_max_node']}")

    cascade = report_dict.get("cascade")
    if cascade:
        assert isinstance(cascade, dict)
        lines.append(f"\n[ Cascade Simulation (seed={cascade['seed']}) ]")
        lines.append(f"  Cascade size : {cascade['size']}")
        lines.append(f"  Reached nodes: {', '.join(str(n) for n in cascade['reached'])}")

    lines.append(f"\n[ Alerts ({len(alerts)}) ]")
    if not alerts:
        lines.append("  No alerts triggered.")
    for a in alerts:
        lines.append(f"  [{a['severity']:8s}] {a['rule']}: {a['message']}")

    lines.append("=" * 60)
    return "\n".join(lines)


def _cmd_report(args: argparse.Namespace) -> None:
    with open(args.input, encoding="utf-8") as fh:
        transfers_data: list[dict[str, object]] = json.load(fh)

    graph = _build_graph(transfers_data)
    report = RiskAnalyzer().analyze(graph)
    alerts = AlertEngine().evaluate(report)
    report_dict = report.to_dict()
    alert_dicts = [a.to_dict() for a in alerts]

    fmt = args.format
    if fmt == "json":
        output = json.dumps({"report": report_dict, "alerts": alert_dicts}, indent=2)
    else:
        output = _format_text(report_dict, alert_dicts)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
            fh.write("\n")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="riskmonitor",
        description="Systemic risk monitor for interbank exposure networks",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # simulate
    p_sim = sub.add_parser("simulate", help="Generate synthetic interbank transfers")
    p_sim.add_argument("--n", type=int, default=100, help="Number of transfers (default: 100)")
    p_sim.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    p_sim.add_argument("--output", "-o", default=None, help="Output JSON file (default: stdout)")

    # analyze
    p_ana = sub.add_parser("analyze", help="Analyze an interbank transfer file")
    p_ana.add_argument("--input", "-i", required=True, help="Input JSON file of transfers")
    p_ana.add_argument("--output", "-o", default=None, help="Output JSON file (default: stdout)")

    # report
    p_rep = sub.add_parser("report", help="Full risk report with alerts")
    p_rep.add_argument("--input", "-i", required=True, help="Input JSON file of transfers")
    p_rep.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format (default: text)"
    )
    p_rep.add_argument("--output", "-o", default=None, help="Output file (default: stdout)")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``riskmonitor`` CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "simulate": _cmd_simulate,
        "analyze": _cmd_analyze,
        "report": _cmd_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
