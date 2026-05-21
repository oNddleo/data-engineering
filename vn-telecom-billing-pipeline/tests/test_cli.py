"""CLI tests for VN telecom billing pipeline."""

from __future__ import annotations

import json
import sys
from io import StringIO

from vntelecom.cli import main


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
        assert "total_charge_vnd" in obj
        assert obj["total_charge_vnd"] >= 0


def test_simulate_n_param() -> None:
    rc, out = _capture(["simulate", "--n", "50"])
    assert rc == 0
    lines = [ln for ln in out.strip().splitlines() if ln]
    assert len(lines) == 50


def test_simulate_deterministic() -> None:
    _, out1 = _capture(["simulate", "--seed", "99"])
    _, out2 = _capture(["simulate", "--seed", "99"])
    assert out1 == out2


def test_no_subcommand_nonzero() -> None:
    rc, _ = _capture([])
    assert rc == 1
