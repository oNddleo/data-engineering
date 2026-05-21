"""CLI tests for hyperloglog-sketch."""

from __future__ import annotations

import json
import sys
from io import StringIO

from hllsketch.cli import main


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
    assert "true_distinct" in obj
    assert "estimated_distinct" in obj
    assert "error_pct" in obj
    assert obj["true_distinct"] == 10_000


def test_simulate_custom_params() -> None:
    rc, out = _capture(["simulate", "--n-distinct", "5000", "--precision", "14"])
    assert rc == 0
    obj = json.loads(out)
    assert obj["true_distinct"] == 5000
    assert obj["error_pct"] < 5.0  # precision=14 guarantees <1% typically


def test_simulate_reproducible() -> None:
    _, out1 = _capture(["simulate", "--seed", "7", "--n-distinct", "1000"])
    _, out2 = _capture(["simulate", "--seed", "7", "--n-distinct", "1000"])
    assert out1 == out2


def test_no_subcommand_returns_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1
