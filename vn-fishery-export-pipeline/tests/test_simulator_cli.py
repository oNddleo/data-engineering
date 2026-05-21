"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vnfishery.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=20, seed=0)) == 20


def test_generate_deterministic() -> None:
    assert generate(n=10, seed=42) == generate(n=10, seed=42)


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnfishery.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-fishery-export-pipeline" in r.stdout


def test_cli_benchmark() -> None:
    r = _run(
        "benchmark",
        "--species",
        "pangasius",
        "--market",
        "US",
        "--grade",
        "A",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["benchmark_usd_cents_per_kg"] > 0


def test_cli_end_to_end(tmp_path: Path) -> None:
    raw_file = tmp_path / "raw.jsonl"
    agg_file = tmp_path / "agg.jsonl"
    dump_file = tmp_path / "dump.jsonl"

    r = _run("simulate", "--n", "40", "--seed", "0", "--output", str(raw_file))
    assert r.returncode == 0, r.stderr

    r = _run("aggregate", "--input", str(raw_file), "--output", str(agg_file))
    assert r.returncode == 0, r.stderr
    assert agg_file.exists()

    r = _run("dumping-watch", "--input", str(raw_file), "--output", str(dump_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["total"] == 40
    assert dump_file.exists()
