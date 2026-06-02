"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnrice.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_varieties() -> None:
    r = _run("varieties")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "JASMINE" in d["varieties"]
    assert "GRADE_1" in d["grades"]


def test_cli_price() -> None:
    r = _run(
        "price",
        "--variety",
        "JASMINE",
        "--grade",
        "GRADE_1",
        "--weight-mt",
        "100",
        "--moisture-pct",
        "14",
        "--price-vnd",
        "7500",
        "--broken-spec",
        "5%",
    )
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["white_rice_mt"] > 0
    assert d["fob_price_usd_mt"] == 650.0


def test_cli_simulate() -> None:
    r = _run("simulate", "--n", "20", "--seed", "0")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["n_lots"] == 20
    assert d["total_fob_usd"] > 0
