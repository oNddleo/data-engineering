"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "retention.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "TTL" in d["policy_kinds"]


def test_cli_simulate_ttl() -> None:
    r = _run(
        "simulate",
        "--n",
        "100",
        "--policy",
        "ttl",
        "--ttl-ms",
        "500000",
        "--now-ms",
        "1000000",
    )
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["before"]["n"] == 100
    assert d["kept"] + d["evicted"] == 100


def test_cli_simulate_max_count() -> None:
    r = _run("simulate", "--n", "50", "--policy", "max-count", "--max-count", "10")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["kept"] <= 10


def test_cli_simulate_max_size() -> None:
    r = _run("simulate", "--n", "50", "--policy", "max-size", "--max-bytes", "500000")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["kept"] + d["evicted"] == 50
