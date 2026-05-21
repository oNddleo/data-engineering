"""CLI for backfill orchestrator."""

from __future__ import annotations

import argparse
import datetime
import json
import sys

from backfill.orchestrator import BackfillJob, BackfillOrchestrator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill orchestrator CLI")
    sub = parser.add_subparsers(dest="command")

    plan_p = sub.add_parser("plan", help="Show partition plan for a date range")
    plan_p.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    plan_p.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    plan_p.add_argument("--step-days", type=int, default=1)
    plan_p.add_argument("--max-concurrency", type=int, default=4)

    run_p = sub.add_parser("run-dry", help="Dry-run: simulate all partitions succeeding")
    run_p.add_argument("--start", required=True)
    run_p.add_argument("--end", required=True)
    run_p.add_argument("--step-days", type=int, default=1)
    run_p.add_argument("--max-concurrency", type=int, default=4)

    args = parser.parse_args(argv)

    if args.command in ("plan", "run-dry"):
        start = datetime.date.fromisoformat(args.start)
        end = datetime.date.fromisoformat(args.end)
        job = BackfillJob(
            job_id="cli-job",
            start_date=start,
            end_date=end,
            step_days=args.step_days,
            max_concurrency=args.max_concurrency,
        )
        orch = BackfillOrchestrator(job)

        if args.command == "plan":
            for p in orch.partitions:
                print(json.dumps(p.to_dict()))
        else:
            # Dry run: all partitions succeed
            orch.run_sync(lambda _d: None)
            progress = orch.progress()
            print(json.dumps(progress))
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
