"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vngrade.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=50, seed=0)) == 50


def test_generate_deterministic() -> None:
    assert generate(n=10, seed=42) == generate(n=10, seed=42)


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vngrade.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-school-grade-pipeline" in r.stdout


def test_cli_end_to_end(tmp_path: Path) -> None:
    sim_file = tmp_path / "reports.jsonl"
    cls_file = tmp_path / "classified.jsonl"

    r = _run("simulate", "--n", "50", "--seed", "0", "--output", str(sim_file))
    assert r.returncode == 0, r.stderr

    r = _run("classify", "--input", str(sim_file), "--output", str(cls_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["count"] == 50
    assert sum(payload["by_classification"].values()) == 50

    r = _run("summarize", "--input", str(sim_file))
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout)
    assert summary["n_reports"] == 50
    assert 0.0 <= summary["avg_gpa"] <= 10.0
