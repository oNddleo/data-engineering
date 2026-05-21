"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lsmmerge.simulator import generate_runs


def test_generate_runs_count() -> None:
    runs = generate_runs(n_runs=4, keys_per_run=5, key_universe=10, seed=0)
    assert len(runs) == 4


def test_generate_runs_deterministic() -> None:
    a = generate_runs(n_runs=3, keys_per_run=10, key_universe=20, seed=42)
    b = generate_runs(n_runs=3, keys_per_run=10, key_universe=20, seed=42)
    assert a == b


def test_generate_runs_internally_sorted() -> None:
    runs = generate_runs(n_runs=5, keys_per_run=15, key_universe=30, seed=1)
    for r in runs:
        keys = [rec.key for rec in r]
        assert keys == sorted(keys)


def test_generate_runs_rejects_bad_args() -> None:
    with pytest.raises(ValueError):
        generate_runs(n_runs=0)
    with pytest.raises(ValueError):
        generate_runs(tombstone_rate=2.0)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "lsmmerge.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "lsm-merge-iterator" in r.stdout


def test_cli_end_to_end(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    out_file = tmp_path / "merged.jsonl"

    r = _run(
        "simulate",
        "--n-runs",
        "4",
        "--keys-per-run",
        "10",
        "--key-universe",
        "20",
        "--seed",
        "0",
        "--output",
        str(runs_dir),
    )
    assert r.returncode == 0, r.stderr
    assert len(list(runs_dir.glob("*.jsonl"))) == 4

    r = _run("merge", "--input", str(runs_dir), "--output", str(out_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["input_runs"] == 4
    assert out_file.exists()


def test_cli_merge_keep_tombstones(tmp_path: Path) -> None:
    """--keep-tombstones produces ≥ as many output records as without."""
    runs_dir = tmp_path / "runs"
    drop_out = tmp_path / "drop.jsonl"
    keep_out = tmp_path / "keep.jsonl"

    r = _run(
        "simulate",
        "--n-runs",
        "3",
        "--keys-per-run",
        "15",
        "--key-universe",
        "30",
        "--tombstone-rate",
        "0.3",
        "--seed",
        "7",
        "--output",
        str(runs_dir),
    )
    assert r.returncode == 0

    r = _run("merge", "--input", str(runs_dir), "--output", str(drop_out))
    assert r.returncode == 0
    r = _run(
        "merge",
        "--input",
        str(runs_dir),
        "--output",
        str(keep_out),
        "--keep-tombstones",
    )
    assert r.returncode == 0

    drop_lines = drop_out.read_text().splitlines()
    keep_lines = keep_out.read_text().splitlines()
    assert len(keep_lines) >= len(drop_lines)
