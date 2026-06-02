"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnpetro.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_fuels() -> None:
    r = _run("fuels")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "RON95-III" in d["fuel_types"]
    assert "SOUTH" in d["regions"]


def test_cli_price() -> None:
    r = _run("price", "--fuel-type", "RON95-III", "--region", "SOUTH", "--cif", "85")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["retail_price_vnd_per_litre"] > 0
    assert d["retail_price_rounded"] % 10 == 0


def test_cli_simulate() -> None:
    r = _run("simulate", "--n", "20", "--seed", "0")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["n_scenarios"] == 20
    assert d["max_retail_vnd_per_litre"] > 0
