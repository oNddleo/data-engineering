"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from ratelimit.simulator import burst_then_idle, constant_rate


def test_constant_rate_size() -> None:
    out = constant_rate(n_keys=3, n_requests=10, interval_ms=100)
    assert len(out) == 30


def test_constant_rate_sorted_by_ts() -> None:
    out = constant_rate(n_keys=3, n_requests=10, interval_ms=100)
    ts = [t for _, t in out]
    assert ts == sorted(ts)


def test_constant_rate_validates() -> None:
    with pytest.raises(ValueError):
        constant_rate(n_keys=0, n_requests=10)


def test_burst_pattern_size() -> None:
    out = burst_then_idle(n_keys=2, n_bursts=3, burst_size=10)
    assert len(out) == 2 * 3 * 10


def test_burst_validates() -> None:
    with pytest.raises(ValueError):
        burst_then_idle(burst_duration_ms=0)


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ratelimit.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "rate-limiter-toolkit" in r.stdout


@pytest.mark.parametrize("algo", ["token", "leaky", "sliding"])
def test_cli_bench(algo: str) -> None:
    r = _run(
        "bench",
        "--algorithm",
        algo,
        "--capacity",
        "5",
        "--rate",
        "10",
        "--window-ms",
        "1000",
        "--keys",
        "1",
        "--requests",
        "20",
        "--interval-ms",
        "10",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["algorithm"] == algo
    assert payload["n_requests"] == 20
    assert 0 <= payload["n_admitted"] <= 20


def test_cli_bench_burst_mode() -> None:
    r = _run(
        "bench",
        "--algorithm",
        "token",
        "--capacity",
        "5",
        "--rate",
        "10",
        "--burst",
        "--n-bursts",
        "3",
        "--burst-size",
        "10",
    )
    assert r.returncode == 0
