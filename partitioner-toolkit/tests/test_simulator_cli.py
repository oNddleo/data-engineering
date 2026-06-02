"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from partitioner.simulator import generate_keys


def test_generate_count() -> None:
    assert len(generate_keys(n=100, alphabet_size=50, seed=0)) == 100


def test_generate_deterministic() -> None:
    a = generate_keys(n=100, alphabet_size=50, seed=42)
    b = generate_keys(n=100, alphabet_size=50, seed=42)
    assert a == b


def test_generate_rejects_bad_args() -> None:
    with pytest.raises(ValueError):
        generate_keys(n=-1)
    with pytest.raises(ValueError):
        generate_keys(n=10, alphabet_size=0)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "partitioner.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "partitioner-toolkit" in r.stdout


def test_cli_range() -> None:
    r = _run("range", "--boundaries", "10,20,30", "5", "15", "25", "35")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_partitions"] == 4
    assert payload["sample"] == {"5": 0, "15": 1, "25": 2, "35": 3}


def test_cli_hash_end_to_end(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    out = tmp_path / "out.jsonl"
    r = _run("simulate", "--n", "200", "--alphabet", "20", "--seed", "0", "--output", str(raw))
    assert r.returncode == 0, r.stderr
    r = _run("hash", "--input", str(raw), "--output", str(out), "--partitions", "8")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_keys"] == 200
    assert sum(payload["counts"].values()) == 200


def test_cli_consistent_end_to_end(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    out = tmp_path / "out.jsonl"
    r = _run("simulate", "--n", "300", "--alphabet", "50", "--seed", "0", "--output", str(raw))
    assert r.returncode == 0
    r = _run(
        "consistent",
        "--input",
        str(raw),
        "--output",
        str(out),
        "--nodes",
        "a",
        "b",
        "c",
        "--replicas",
        "64",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_keys"] == 300
    assert sum(payload["counts"].values()) == 300
