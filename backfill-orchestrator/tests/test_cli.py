"""CLI tests for backfill orchestrator."""

from __future__ import annotations

import json
import sys
from io import StringIO

from backfill.cli import main


def _capture(argv: list[str]) -> tuple[int, str]:
    old_out = sys.stdout
    sys.stdout = buf = StringIO()
    try:
        rc = main(argv)
    finally:
        sys.stdout = old_out
    return rc, buf.getvalue()


def test_plan_7_days() -> None:
    rc, out = _capture(["plan", "--start", "2025-01-01", "--end", "2025-01-07"])
    assert rc == 0
    lines = [ln for ln in out.strip().splitlines() if ln]
    assert len(lines) == 7
    for line in lines:
        obj = json.loads(line)
        assert obj["state"] == "PENDING"


def test_run_dry_all_done() -> None:
    rc, out = _capture(["run-dry", "--start", "2025-03-01", "--end", "2025-03-05"])
    assert rc == 0
    obj = json.loads(out)
    assert obj["DONE"] == 5
    assert obj["FAILED"] == 0


def test_no_subcommand_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1


def test_plan_step_days() -> None:
    rc, out = _capture(
        ["plan", "--start", "2025-01-01", "--end", "2025-01-15", "--step-days", "7"]
    )
    assert rc == 0
    lines = [ln for ln in out.strip().splitlines() if ln]
    assert len(lines) == 3  # Jan 1, 8, 15
