"""CLI tests for circuit breaker toolkit."""

from __future__ import annotations

import json
import sys
from io import StringIO

from circuitbreaker.cli import main


def _capture(argv: list[str]) -> tuple[int, str]:
    old_out = sys.stdout
    sys.stdout = buf = StringIO()
    try:
        rc = main(argv)
    finally:
        sys.stdout = old_out
    return rc, buf.getvalue()


def test_simulate_default() -> None:
    rc, out = _capture(["simulate"])
    assert rc == 0
    obj = json.loads(out)
    assert "total_calls" in obj
    assert "final_state" in obj
    assert obj["total_calls"] == 50


def test_simulate_no_failures() -> None:
    rc, out = _capture(["simulate", "--failure-rate", "0.0"])
    assert rc == 0
    obj = json.loads(out)
    assert obj["final_state"] == "CLOSED"
    assert obj["failed_calls"] == 0


def test_no_subcommand_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1


def test_simulate_deterministic() -> None:
    _, out1 = _capture(["simulate", "--seed", "1"])
    _, out2 = _capture(["simulate", "--seed", "1"])
    assert out1 == out2
