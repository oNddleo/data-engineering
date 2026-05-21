"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from idempotency.simulator import generate


def test_generate_count() -> None:
    assert len(generate(n_unique=10, n_total=50, seed=0)) == 50


def test_generate_deterministic() -> None:
    a = generate(n_unique=20, n_total=100, seed=42)
    b = generate(n_unique=20, n_total=100, seed=42)
    assert a == b


def test_generate_rejects_bad_args() -> None:
    with pytest.raises(ValueError):
        generate(n_unique=0)
    with pytest.raises(ValueError):
        generate(n_unique=10, n_total=-1)


def test_generate_keys_in_universe() -> None:
    rs = generate(n_unique=10, n_total=100, seed=0)
    unique_keys = {r.key for r in rs}
    assert len(unique_keys) <= 10


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "idempotency.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "idempotency-key-store" in r.stdout


def test_cli_fingerprint() -> None:
    r = _run("fingerprint", "hello")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert len(payload["fingerprint"]) == 16


def test_cli_simulate_run() -> None:
    r = _run(
        "simulate-run",
        "--unique",
        "20",
        "--total",
        "200",
        "--seed",
        "0",
        "--ttl-ms",
        "100000",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_requests"] == 200
    # With 20 unique keys and 200 requests, we should see lots of replays.
    assert payload["outcomes"]["new"] <= 20
    assert payload["outcomes"]["replay_success"] >= 100
