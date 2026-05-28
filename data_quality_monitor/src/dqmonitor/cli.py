"""CLI entry-point for dqmonitor.

Subcommands
-----------
validate --input FILE --suite FILE
    Load a JSONL input file and an ExpectationSuite JSON file, run validation,
    and print a summary.

status
    Print current gate status from the most recent audit entry.

audit [--last N]
    Print the last N audit entries (default 10).

reset
    Clear the audit log and reset the gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_DEFAULT_AUDIT = Path.home() / ".dqmonitor" / "audit.jsonl"


def _get_audit_path(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "audit_file", None) or _DEFAULT_AUDIT)


def cmd_validate(args: argparse.Namespace) -> int:
    from dqmonitor.audit import AuditLog
    from dqmonitor.expectations import ExpectationSuite
    from dqmonitor.gate import QualityGate
    from dqmonitor.monitor import QualityMonitor

    input_path = Path(args.input)
    suite_path = Path(args.suite)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1
    if not suite_path.exists():
        print(f"ERROR: suite file not found: {suite_path}", file=sys.stderr)
        return 1

    # Load records (one JSON object per line)
    batch: list[dict[str, object]] = []
    with input_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                batch.append(json.loads(line))

    suite = ExpectationSuite.from_json(suite_path.read_text(encoding="utf-8"))
    gate = QualityGate(threshold=getattr(args, "threshold", 0.95))
    audit_log = AuditLog(_get_audit_path(args))
    monitor = QualityMonitor(suite=suite, gate=gate, audit_log=audit_log)

    result = monitor.process_batch(batch, suite_name=suite.name)

    print(f"Records : {result.total}")
    print(f"Passed  : {result.passed}")
    print(f"Failed  : {result.failed}")
    print(f"Pass rate: {result.pass_rate:.2%}")
    print(f"Gate    : {'BLOCKED' if gate.is_blocked() else 'OPEN'}")
    if result.violations:
        print(f"\nViolations ({len(result.violations)}):")
        for v in result.violations[:20]:
            print(f"  [row {v.record_index}] rule={v.rule_name!r} value={v.value!r}")
        if len(result.violations) > 20:
            print(f"  ... and {len(result.violations) - 20} more")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from dqmonitor.audit import AuditLog

    audit_log = AuditLog(_get_audit_path(args))
    runs = audit_log.query(last_n=1)
    if not runs:
        print("No audit entries found.")
        return 0
    run = runs[-1]
    print(f"Last run  : {run.timestamp}")
    print(f"Suite     : {run.suite_name}")
    print(f"Pass rate : {run.pass_rate:.2%}")
    print(f"Gate      : {run.gate_status.upper()}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from dqmonitor.audit import AuditLog

    last_n: int = getattr(args, "last", 10)
    audit_log = AuditLog(_get_audit_path(args))
    runs = audit_log.query(last_n=last_n)
    if not runs:
        print("No audit entries found.")
        return 0
    for run in runs:
        print(
            f"{run.timestamp}  suite={run.suite_name!r:<20}"
            f"  pass_rate={run.pass_rate:.2%}  gate={run.gate_status}"
            f"  total={run.total}  failed={run.failed}"
        )
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    from dqmonitor.audit import AuditLog

    audit_log = AuditLog(_get_audit_path(args))
    audit_log.clear()
    print("Audit log cleared.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dqmonitor",
        description="Data Quality Monitor CLI",
    )
    parser.add_argument(
        "--audit-file",
        default=str(_DEFAULT_AUDIT),
        metavar="FILE",
        help="Path to the JSONL audit log (default: ~/.dqmonitor/audit.jsonl)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = sub.add_parser("validate", help="Run validation on an input file")
    p_val.add_argument("--input", required=True, metavar="FILE", help="JSONL records file")
    p_val.add_argument("--suite", required=True, metavar="FILE", help="ExpectationSuite JSON")
    p_val.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        metavar="FLOAT",
        help="Gate threshold (default 0.95)",
    )

    # status
    sub.add_parser("status", help="Show current gate status")

    # audit
    p_audit = sub.add_parser("audit", help="Show recent audit entries")
    p_audit.add_argument(
        "--last",
        type=int,
        default=10,
        metavar="N",
        help="Number of entries to show (default 10)",
    )

    # reset
    sub.add_parser("reset", help="Clear the audit log")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "validate": cmd_validate,
        "status": cmd_status,
        "audit": cmd_audit,
        "reset": cmd_reset,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
