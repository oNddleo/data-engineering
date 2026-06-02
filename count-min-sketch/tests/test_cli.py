"""CLI tests for count-min-sketch."""

from __future__ import annotations

import json
import sys
from io import StringIO

from cmsketch.cli import main


def _capture(argv: list[str]) -> tuple[int, str]:
    old_out = sys.stdout
    sys.stdout = buf = StringIO()
    try:
        rc = main(argv)
    finally:
        sys.stdout = old_out
    return rc, buf.getvalue()


def test_simulate_default() -> None:
    rc, _ = _capture(["simulate"])
    assert rc == 0


def test_simulate_outputs_jsonl() -> None:
    rc, out = _capture(["simulate", "--n-items", "500", "--vocab-size", "50", "--top-k", "5"])
    assert rc == 0
    lines = [line for line in out.strip().splitlines() if line]
    assert len(lines) == 5
    for line in lines:
        obj = json.loads(line)
        assert "item" in obj
        assert "true_count" in obj
        assert "estimated_count" in obj
        assert obj["estimated_count"] >= obj["true_count"]
        assert obj["overcount"] == obj["estimated_count"] - obj["true_count"]


def test_no_subcommand_returns_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1


def test_simulate_same_seed_deterministic() -> None:
    _, out1 = _capture(["simulate", "--seed", "1", "--n-items", "200", "--top-k", "3"])
    _, out2 = _capture(["simulate", "--seed", "1", "--n-items", "200", "--top-k", "3"])
    assert out1 == out2


def test_simulate_no_crash_with_different_seeds() -> None:
    _, out1 = _capture(["simulate", "--seed", "10", "--n-items", "500", "--top-k", "5"])
    _, out2 = _capture(["simulate", "--seed", "99", "--n-items", "500", "--top-k", "5"])
    # Both should produce valid JSONL output
    assert len(out1.strip().splitlines()) == 5
    assert len(out2.strip().splitlines()) == 5
