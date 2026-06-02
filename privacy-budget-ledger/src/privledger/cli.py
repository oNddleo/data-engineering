"""CLI for privledger: query, status, audit, reset subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from privledger.audit import AuditLog
from privledger.ledger import BudgetLedger
from privledger.mechanisms import GaussianMechanism
from privledger.planner import QueryPlanner, QueryRequest

_DEFAULT_STATE = Path.home() / ".privledger" / "state.json"
_DEFAULT_AUDIT = Path.home() / ".privledger" / "audit.jsonl"
_DEFAULT_EPSILON = 10.0
_DEFAULT_DELTA = 1e-6


def _load_ledger(state_path: Path) -> BudgetLedger:
    ledger = BudgetLedger()
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        # Reconstruct stored limits; accountants are not persisted (audit log is)
        for key_str, info in data.items():
            ds, an = key_str.split("|||", 1)
            ledger.set_limit(ds, an, info["epsilon_limit"])
    return ledger


def _save_ledger(ledger: BudgetLedger, state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, dict[str, float]] = {}
    for ds, an in ledger.keys:
        bud = ledger._budgets[(ds, an)]
        data[f"{ds}|||{an}"] = {"epsilon_limit": bud.epsilon_limit}
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cmd_query(args: argparse.Namespace) -> int:
    """Execute a single query request."""
    state_path: Path = args.state
    audit_path: Path = args.audit_path

    state_path.parent.mkdir(parents=True, exist_ok=True)

    ledger = _load_ledger(state_path)
    audit_log = AuditLog(persist_path=audit_path)
    planner = QueryPlanner()

    if args.epsilon_limit:
        ledger.set_limit(args.dataset, args.analyst, args.epsilon_limit)

    request = QueryRequest(
        query_id=args.query_id or "",
        dataset=args.dataset,
        analyst=args.analyst,
        sensitivity=args.sensitivity,
        sigma=args.sigma,
        delta=args.delta,
    )

    budget_remaining = ledger.remaining_epsilon(
        dataset=args.dataset,
        analyst=args.analyst,
        accountant="basic",
        delta=args.delta,
    )

    decision, new_sigma = planner.plan(request, budget_remaining)
    print(f"Decision: {decision}")

    if decision == "reject":
        print("Query REJECTED: no sigma fits within remaining budget.")
        return 1

    effective_sigma = new_sigma if new_sigma is not None else request.sigma
    if decision == "rewrite":
        print(
            f"Query REWRITTEN: sigma increased from {request.sigma:.4f}"
            f" to {effective_sigma:.4f}"
        )

    mechanism = GaussianMechanism(args.sensitivity, effective_sigma)
    try:
        ledger.spend(
            mechanism,
            request.query_id or "cli",
            dataset=args.dataset,
            analyst=args.analyst,
            delta=args.delta,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    entry = audit_log.record(
        dataset=args.dataset,
        analyst=args.analyst,
        mechanism=mechanism,
        delta=args.delta,
        query_id=request.query_id or None,
    )
    _save_ledger(ledger, state_path)

    print(f"  epsilon_basic : {entry.epsilon_basic:.6f}")
    print(f"  epsilon_rdp   : {entry.epsilon_rdp:.6f}")
    print(f"  epsilon_zcdp  : {entry.epsilon_zcdp:.6f}")
    print(f"  savings (rdp vs basic): {entry.savings_vs_basic:.6f}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show budget status for a (dataset, analyst) pair."""
    ledger = _load_ledger(args.state)
    status = ledger.status(dataset=args.dataset, analyst=args.analyst, delta=args.delta)
    print(json.dumps(status, indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Show the audit log, optionally filtered."""
    audit_log = AuditLog(persist_path=args.audit_path)
    entries = audit_log.filter(
        dataset=args.dataset if hasattr(args, "dataset") else None,
        analyst=args.analyst if hasattr(args, "analyst") else None,
    )
    for entry in entries:
        print(entry.to_json())
    print(f"# {len(entries)} entries", file=sys.stderr)
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset the state and/or audit log."""
    if args.state.exists():
        args.state.unlink()
        print(f"Removed state: {args.state}")
    if args.audit_path.exists() and args.clear_audit:
        args.audit_path.unlink()
        print(f"Removed audit log: {args.audit_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="privledger",
        description="Differential privacy budget ledger CLI",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=_DEFAULT_STATE,
        help="Path to state JSON file (default: ~/.privledger/state.json)",
    )
    parser.add_argument(
        "--audit-path",
        type=Path,
        default=_DEFAULT_AUDIT,
        dest="audit_path",
        help="Path to audit JSONL file (default: ~/.privledger/audit.jsonl)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ---- query -----------------------------------------------------------
    q = sub.add_parser("query", help="Execute a privacy-aware query")
    q.add_argument("--dataset", required=True, help="Dataset identifier")
    q.add_argument("--analyst", required=True, help="Analyst identifier")
    q.add_argument("--sensitivity", type=float, required=True, help="Query L2 sensitivity")
    q.add_argument("--sigma", type=float, required=True, help="Gaussian noise sigma")
    q.add_argument("--delta", type=float, default=_DEFAULT_DELTA, help="Delta for (ε,δ)-DP")
    q.add_argument(
        "--epsilon-limit",
        type=float,
        default=None,
        dest="epsilon_limit",
        help="Override epsilon budget limit for this (dataset, analyst)",
    )
    q.add_argument("--query-id", default=None, dest="query_id", help="Optional query identifier")
    q.set_defaults(func=cmd_query)

    # ---- status ----------------------------------------------------------
    s = sub.add_parser("status", help="Show budget status")
    s.add_argument("--dataset", required=True)
    s.add_argument("--analyst", required=True)
    s.add_argument("--delta", type=float, default=_DEFAULT_DELTA)
    s.set_defaults(func=cmd_status)

    # ---- audit -----------------------------------------------------------
    a = sub.add_parser("audit", help="Show audit log")
    a.add_argument("--dataset", default=None)
    a.add_argument("--analyst", default=None)
    a.set_defaults(func=cmd_audit)

    # ---- reset -----------------------------------------------------------
    r = sub.add_parser("reset", help="Reset ledger state")
    r.add_argument(
        "--clear-audit", action="store_true", dest="clear_audit", help="Also delete the audit log"
    )
    r.set_defaults(func=cmd_reset)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
