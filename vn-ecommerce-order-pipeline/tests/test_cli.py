"""CLI tests for VN e-commerce order pipeline."""

from __future__ import annotations

import json
import sys
from io import StringIO

from vnecommerce.cli import main


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
    lines = [ln for ln in out.strip().splitlines() if ln]
    assert len(lines) == 100
    for line in lines:
        obj = json.loads(line)
        assert "platform" in obj
        assert "status" in obj
        assert "buyer_paid_vnd" in obj


def test_simulate_n_param() -> None:
    rc, out = _capture(["simulate", "--n", "10"])
    assert rc == 0
    lines = [ln for ln in out.strip().splitlines() if ln]
    assert len(lines) == 10


def test_simulate_deterministic() -> None:
    _, out1 = _capture(["simulate", "--seed", "7", "--n", "20"])
    _, out2 = _capture(["simulate", "--seed", "7", "--n", "20"])
    assert out1 == out2


def test_no_subcommand_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1
