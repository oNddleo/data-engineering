"""CLI for the exactly-once pipeline package."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from exactlyonce.coordinator import TransactionCoordinator
from exactlyonce.dlq import DeadLetterQueue
from exactlyonce.idempotency import IdempotencyLog
from exactlyonce.outbox import OutboxStore
from exactlyonce.pipeline import ExactlyOncePipeline
from exactlyonce.recovery import RecoveryAgent

# Default persistence directory
_DEFAULT_DIR = Path.home() / ".exactlyonce"


def _build_pipeline(data_dir: Path) -> ExactlyOncePipeline:
    data_dir.mkdir(parents=True, exist_ok=True)
    return ExactlyOncePipeline(
        idempotency_log=IdempotencyLog(data_dir / "idempotency.jsonl"),
        outbox=OutboxStore(data_dir / "outbox.jsonl"),
        coordinator=TransactionCoordinator(data_dir / "coordinator.jsonl"),
    )


def _cmd_submit(args: argparse.Namespace) -> int:
    """Submit an event for exactly-once processing."""
    data_dir: Path = args.data_dir
    try:
        payload: dict[str, object] = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON payload — {exc}", file=sys.stderr)
        return 1

    if "event_id" not in payload:
        payload["event_id"] = str(uuid.uuid4())

    pipeline = _build_pipeline(data_dir)
    result = pipeline.process(payload)

    if result.skipped_duplicate:
        print(f"Duplicate: event {payload['event_id']} already processed.")
    else:
        print(f"Submitted: saga_id={result.saga_id}, status={result.status.value}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Show the status of a saga."""
    data_dir: Path = args.data_dir
    coordinator = TransactionCoordinator(data_dir / "coordinator.jsonl")
    saga = coordinator.get(args.saga_id)
    if saga is None:
        print(f"No saga found for id: {args.saga_id}", file=sys.stderr)
        return 1
    print(json.dumps(saga.to_dict(), indent=2))
    return 0


def _cmd_recover(args: argparse.Namespace) -> int:
    """Scan for and recover stuck sagas."""
    data_dir: Path = args.data_dir
    coordinator = TransactionCoordinator(data_dir / "coordinator.jsonl")
    dlq = DeadLetterQueue(data_dir / "dlq.jsonl")
    agent = RecoveryAgent()
    timeout: float = args.timeout
    stuck = agent.scan(coordinator, timeout_seconds=timeout)
    if not stuck:
        print("No stuck sagas found.")
        return 0
    for saga_id in stuck:
        agent.recover(saga_id, coordinator, dlq)
        print(f"Recovered saga: {saga_id}")
    return 0


def _cmd_dlq(args: argparse.Namespace) -> int:
    """Show or drain the dead-letter queue."""
    data_dir: Path = args.data_dir
    dlq = DeadLetterQueue(data_dir / "dlq.jsonl")
    if args.drain:
        entries = dlq.drain(max=args.max)
        if not entries:
            print("DLQ is empty.")
        for entry in entries:
            print(json.dumps(entry.to_dict(), indent=2))
    else:
        print(f"DLQ size: {dlq.count()}")
        for entry in dlq.all_entries():
            print(json.dumps(entry.to_dict(), indent=2))
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="exactlyonce",
        description="Exactly-once pipeline CLI",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=_DEFAULT_DIR,
        metavar="DIR",
        help="Directory for persistence files (default: ~/.exactlyonce)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    p_submit = sub.add_parser("submit", help="Submit an event")
    p_submit.add_argument(
        "--payload",
        required=True,
        metavar="JSON",
        help='JSON payload, e.g. \'{"id":"x","amount":100}\'',
    )

    # status
    p_status = sub.add_parser("status", help="Show saga status")
    p_status.add_argument("--saga-id", required=True, metavar="UUID")

    # recover
    p_recover = sub.add_parser("recover", help="Recover stuck sagas")
    p_recover.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Timeout in seconds before a saga is considered stuck (default: 60)",
    )

    # dlq
    p_dlq = sub.add_parser("dlq", help="Inspect or drain the dead-letter queue")
    p_dlq.add_argument(
        "--drain",
        action="store_true",
        help="Drain (remove) entries from the DLQ",
    )
    p_dlq.add_argument(
        "--max",
        type=int,
        default=100,
        metavar="N",
        help="Maximum entries to drain (default: 100)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the exactlyonce CLI."""
    args = _parse_args(argv)
    dispatch = {
        "submit": _cmd_submit,
        "status": _cmd_status,
        "recover": _cmd_recover,
        "dlq": _cmd_dlq,
    }
    handler = dispatch[args.command]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
