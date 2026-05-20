"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vnprop.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=10, seed=0)) == 10


def test_generate_deterministic() -> None:
    assert generate(n=5, seed=42) == generate(n=5, seed=42)


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnprop.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-property-listing-normalizer" in r.stdout


def test_cli_price() -> None:
    r = _run("price", "2.5 tỷ")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["value_vnd"] == 2_500_000_000


def test_cli_area() -> None:
    r = _run("area", "75m²")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["area_m2"] == 75


def test_cli_end_to_end(tmp_path: Path) -> None:
    raw_file = tmp_path / "raw.jsonl"
    out_file = tmp_path / "out.jsonl"
    r = _run("simulate", "--n", "10", "--seed", "0", "--output", str(raw_file))
    assert r.returncode == 0
    r = _run("normalize", "--input", str(raw_file), "--output", str(out_file))
    assert r.returncode == 0
    assert out_file.exists()
