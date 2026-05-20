"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vnride.simulator import generate


def test_generate_default() -> None:
    trips = generate(n_riders=5, n_drivers=3, n_days=2, seed=0)
    assert len(trips) > 0


def test_generate_deterministic() -> None:
    a = generate(n_riders=5, n_drivers=3, n_days=2, seed=42)
    b = generate(n_riders=5, n_drivers=3, n_days=2, seed=42)
    assert a == b


def test_generate_validates() -> None:
    with pytest.raises(ValueError, match="n_riders"):
        generate(n_riders=-1)
    with pytest.raises(ValueError, match="n_days"):
        generate(n_days=0)
    with pytest.raises(ValueError, match="ghost_fraction"):
        generate(ghost_fraction=1.5)


def test_generate_sorted_by_time() -> None:
    trips = generate(n_riders=5, n_drivers=3, n_days=3, seed=0)
    times = [t.requested_at for t in trips]
    assert times == sorted(times)


def test_generate_state_distribution() -> None:
    """A sufficiently large run should produce all three terminal states."""
    from vnride.schema import TripState

    trips = generate(n_riders=80, n_drivers=20, n_days=10, seed=7)
    states = {t.state for t in trips}
    assert TripState.COMPLETED in states
    assert TripState.CANCELLED in states
    assert TripState.NO_DRIVER in states


def test_generate_injects_fraud_when_fractions_high() -> None:
    """At elevated fractions, fraud detectors must fire."""
    from vnride.fraud import (
        find_cancellation_abuse,
        find_ghost_rides,
    )

    trips = generate(
        n_riders=80,
        n_drivers=20,
        n_days=14,
        seed=11,
        ghost_fraction=0.20,
        cancel_abuse_fraction=0.20,
    )
    assert len(find_ghost_rides(trips)) >= 1
    assert len(find_cancellation_abuse(trips)) >= 1


# ---------- CLI -------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vnride.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_info() -> None:
    r = _run("info")
    assert r.returncode == 0
    assert "vn-ride-hailing-trip-pipeline" in r.stdout


def test_cli_operators() -> None:
    r = _run("operators")
    assert r.returncode == 0
    assert "GRAB" in r.stdout
    assert "BE" in r.stdout


def test_cli_cities() -> None:
    r = _run("cities")
    assert r.returncode == 0
    assert "SGN" in r.stdout
    assert "HAN" in r.stdout


def test_cli_quote() -> None:
    r = _run(
        "quote",
        "--service",
        "CAR",
        "--km",
        "5.0",
        "--minutes",
        "15",
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["total_vnd"] > 0
    assert payload["surge_multiplier"] == 1.0


def test_cli_end_to_end(tmp_path: Path) -> None:
    trip_file = tmp_path / "trips.jsonl"
    settle_file = tmp_path / "settlements.jsonl"

    r = _run(
        "simulate",
        "--riders",
        "10",
        "--drivers",
        "5",
        "--days",
        "3",
        "--seed",
        "7",
        "--output",
        str(trip_file),
    )
    assert r.returncode == 0, r.stderr
    assert trip_file.exists()

    r = _run(
        "settle",
        "--input",
        str(trip_file),
        "--output",
        str(settle_file),
        "--show",
        "0",
    )
    assert r.returncode == 0, r.stderr
    assert settle_file.exists()

    r = _run("summary", "--input", str(trip_file))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_trips"] > 0
    assert payload["n_riders"] == 10


def test_cli_fraud_exit_code(tmp_path: Path) -> None:
    """Fraud command exits 2 when findings present, else 0."""
    trip_file = tmp_path / "trips.jsonl"
    r = _run(
        "simulate",
        "--riders",
        "50",
        "--drivers",
        "15",
        "--days",
        "10",
        "--seed",
        "11",
        "--output",
        str(trip_file),
    )
    assert r.returncode == 0
    r = _run("fraud", "--input", str(trip_file), "--show", "0")
    assert r.returncode in (0, 2), r.stderr
