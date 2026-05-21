"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vncoffee.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_grades() -> None:
    r = _run("grades")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "ROBUSTA" in d["species"]
    assert "R1" in d["grades"]


def test_cli_price() -> None:
    r = _run(
        "price",
        "--lot-id",
        "T001",
        "--species",
        "ROBUSTA",
        "--grade",
        "R1",
        "--contract",
        "DIFFERENTIAL",
        "--incoterm",
        "FOB",
        "--volume-mt",
        "100",
        "--futures-price",
        "3000",
        "--differential",
        "50",
    )
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["fob_price_usd_mt"] == 3050.0
    assert d["total_fob_usd"] == 305_000.0


def test_cli_simulate() -> None:
    r = _run("simulate", "--n", "20", "--seed", "42")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["n_lots"] == 20
    assert d["total_volume_mt"] > 0
