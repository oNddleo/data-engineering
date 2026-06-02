"""CLI entry point: selfheal run | demo | status."""

from __future__ import annotations

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    """Process JSONL records from stdin (or a file)."""
    from .alerts.alerter import ConsoleAlerter  # noqa: PLC0415
    from .pipeline.runner import PipelineRunner  # noqa: PLC0415
    from .quarantine.store import QuarantineStore  # noqa: PLC0415
    from .schema.registry import SchemaRegistry  # noqa: PLC0415

    source: str = args.source
    input_stream = sys.stdin if args.input == "-" else open(args.input)  # noqa: WPS515

    try:
        records: list[dict[str, object]] = []
        for lineno, line in enumerate(input_stream, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[ERROR] Line {lineno}: invalid JSON — {exc}", file=sys.stderr)
                continue
            if not isinstance(record, dict):
                print(
                    f"[ERROR] Line {lineno}: expected JSON object, got {type(record).__name__}",
                    file=sys.stderr,
                )
                continue
            records.append(record)
    finally:
        if args.input != "-":
            input_stream.close()

    registry = SchemaRegistry()
    quarantine = QuarantineStore()
    alerter = ConsoleAlerter()
    runner = PipelineRunner(registry, source, quarantine, alerter)
    result = runner.run(records)

    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "loaded": result.loaded,
                "quarantined": result.quarantined,
                "healed": result.healed,
                "drift_events": len(result.drift_events),
            },
            indent=2,
        )
    )
    return 0


def cmd_demo(_args: argparse.Namespace) -> int:
    """Run a built-in 3-batch demo that showcases drift detection and healing."""
    from .alerts.alerter import ConsoleAlerter  # noqa: PLC0415
    from .pipeline.runner import PipelineRunner  # noqa: PLC0415
    from .quarantine.store import QuarantineStore  # noqa: PLC0415
    from .schema.registry import SchemaRegistry  # noqa: PLC0415

    print("=" * 60)
    print("  Self-Healing ETL — built-in demo")
    print("=" * 60)

    registry = SchemaRegistry()
    quarantine = QuarantineStore()
    alerter = ConsoleAlerter()
    source = "demo_orders"
    runner = PipelineRunner(registry, source, quarantine, alerter)

    # --- Batch 1: clean baseline ---
    print("\n[Batch 1] Clean baseline — establishing schema")
    batch1: list[dict[str, object]] = [
        {"id": 1, "customer": "Alice", "amount": 99.99},
        {"id": 2, "customer": "Bob", "amount": 149.0},
        {"id": 3, "customer": "Carol", "amount": 9.0},
    ]
    r1 = runner.run(batch1)
    print(f"  loaded={r1.loaded}  quarantined={r1.quarantined}  healed={r1.healed}")

    # --- Batch 2: column added + type changed ---
    print("\n[Batch 2] New 'status' column added; 'amount' type changed str→float")
    batch2: list[dict[str, object]] = [
        {"id": 4, "customer": "Dave", "amount": "250.00", "status": "pending"},
        {"id": 5, "customer": "Eve", "amount": "75.50", "status": "shipped"},
    ]
    r2 = runner.run(batch2)
    print(f"  loaded={r2.loaded}  quarantined={r2.quarantined}  healed={r2.healed}")

    # --- Batch 3: column removed ---
    print("\n[Batch 3] 'customer' column removed — backfill strategy")
    batch3: list[dict[str, object]] = [
        {"id": 6, "amount": 300.0, "status": "delivered"},
        {"id": 7, "amount": 55.0, "status": "pending"},
    ]
    r3 = runner.run(batch3)
    print(f"  loaded={r3.loaded}  quarantined={r3.quarantined}  healed={r3.healed}")

    print("\n--- Quarantine summary ---")
    print(f"  Total quarantined records: {quarantine.count()}")
    for etype, cnt in quarantine.count_by_error_type().items():
        print(f"    {etype}: {cnt}")

    print("\n--- Schema history ---")
    for entry in registry.get_history(source):
        print(f"  v{entry.version}  {entry.schema}")

    print("\n" + "=" * 60)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show schema versions for sources in a registry JSON file."""
    import pathlib  # noqa: PLC0415

    from .schema.registry import SchemaRegistry  # noqa: PLC0415

    path = pathlib.Path(args.registry_file)
    if not path.exists():
        print(f"[ERROR] Registry file not found: {path}", file=sys.stderr)
        return 1

    registry = SchemaRegistry.from_json(path.read_text())
    sources = registry.sources()

    if not sources:
        print("No sources registered.")
        return 0

    for source_name in sources:
        history = registry.get_history(source_name)
        active = registry.get_active(source_name)
        active_ver = active.version if active else "—"
        print(f"\nSource: {source_name!r}  (active=v{active_ver})")
        for entry in history:
            marker = " ◄ active" if entry.is_active and entry.version == active_ver else ""
            print(f"  v{entry.version}  {entry.schema}{marker}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="selfheal",
        description="Self-healing ETL framework",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    run_p = sub.add_parser("run", help="Process JSONL records")
    run_p.add_argument("--source", default="default", help="Source name")
    run_p.add_argument(
        "--input",
        default="-",
        help="Path to JSONL file, or '-' for stdin (default)",
    )

    # demo
    sub.add_parser("demo", help="Run built-in 3-batch demo")

    # status
    status_p = sub.add_parser("status", help="Show schema versions")
    status_p.add_argument("registry_file", help="Path to registry JSON file")

    return parser


def main() -> None:
    """Entry point for the ``selfheal`` console script."""
    parser = _build_parser()
    args = parser.parse_args()
    dispatch = {
        "run": cmd_run,
        "demo": cmd_demo,
        "status": cmd_status,
    }
    handler = dispatch[args.command]
    sys.exit(handler(args))
