"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bloomdedup.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=100, n_unique=10, duplicate_rate=0.5, seed=0)) == 100


def test_generate_deterministic() -> None:
    a = generate(n=100, n_unique=20, duplicate_rate=0.5, seed=42)
    b = generate(n=100, n_unique=20, duplicate_rate=0.5, seed=42)
    assert a == b


def test_generate_high_duplication() -> None:
    """High duplicate_rate should yield fewer unique keys."""
    out = generate(n=1000, n_unique=100, duplicate_rate=0.95, seed=0)
    assert len(set(out)) < 100  # most repeats


def test_generate_rejects_bad_args() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)
    with pytest.raises(ValueError):
        generate(n=10, n_unique=0)
    with pytest.raises(ValueError):
        generate(n=10, duplicate_rate=1.5)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bloomdedup.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "dedup-with-bloom" in r.stdout


def test_cli_params() -> None:
    r = _run("params", "--capacity", "1000", "--fpr", "0.01")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["capacity"] == 1000
    assert payload["m_bits"] > 0


def test_cli_end_to_end(tmp_path: Path) -> None:
    raw_file = tmp_path / "raw.jsonl"
    out_file = tmp_path / "out.jsonl"

    r = _run(
        "simulate",
        "--n",
        "200",
        "--unique",
        "20",
        "--duplicate-rate",
        "0.5",
        "--seed",
        "0",
        "--output",
        str(raw_file),
    )
    assert r.returncode == 0, r.stderr

    r = _run(
        "dedup",
        "--input",
        str(raw_file),
        "--output",
        str(out_file),
        "--capacity",
        "200",
        "--fpr",
        "0.001",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["seen"] == 200
    assert payload["kept"] <= 20  # at most n_unique
    assert payload["suppressed"] >= 180
