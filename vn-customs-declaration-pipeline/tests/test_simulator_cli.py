"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vncustoms.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=10, seed=0)) == 10


def test_generate_deterministic() -> None:
    assert generate(n=5, seed=42) == generate(n=5, seed=42)


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vncustoms.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-customs-declaration-pipeline" in r.stdout


def test_cli_tariff() -> None:
    r = _run("tariff", "85")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["chapter"] == "85"
    assert payload["duty_rate"] > 0
    assert payload["vat_rate"] > 0


def test_cli_end_to_end(tmp_path: Path) -> None:
    sim_file = tmp_path / "decls.jsonl"
    calc_file = tmp_path / "calc.jsonl"
    r = _run("simulate", "--n", "8", "--seed", "0", "--output", str(sim_file))
    assert r.returncode == 0, r.stderr
    r = _run("calc", "--input", str(sim_file), "--output", str(calc_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["count"] == 8
    assert payload["total_tax_vnd"] >= 0
    assert calc_file.exists()
