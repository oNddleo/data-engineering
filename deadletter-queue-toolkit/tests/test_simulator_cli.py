"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dlq.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n=20, seed=0)) == 20


def test_generate_deterministic() -> None:
    assert generate(n=10, seed=42) == generate(n=10, seed=42)


def test_generate_classification_consistent() -> None:
    """Every generated DL has a failure_kind that matches classify(error)."""
    from dlq.schema import classify

    for dl in generate(n=30, seed=0):
        assert classify(dl.error_message) == dl.failure_kind


def test_generate_rejects_negative() -> None:
    with pytest.raises(ValueError):
        generate(n=-1)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dlq.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "deadletter-queue-toolkit" in r.stdout


def test_cli_classify() -> None:
    r = _run("classify", "503 Service Unavailable")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["kind"] == "transient"


def test_cli_backoff() -> None:
    r = _run("backoff", "--max-attempts", "5", "--jitter", "none", "--seed", "0")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["schedule_ms"] == [100, 200, 400, 800, 1600]


def test_cli_end_to_end(tmp_path: Path) -> None:
    sim_file = tmp_path / "dlq.jsonl"
    r = _run("simulate", "--n", "30", "--seed", "0", "--output", str(sim_file))
    assert r.returncode == 0, r.stderr
    r = _run("summarize", "--input", str(sim_file))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["total"] == 30
    assert sum(payload["by_kind"].values()) == 30
