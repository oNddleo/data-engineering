"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vntrip.schema import TripEventKind
from vntrip.simulator import generate
from vntrip.state import stitch


def test_simulator_deterministic():
    a = generate(n_riders=20, n_drivers=8, n_days=3, seed=42)
    b = generate(n_riders=20, n_drivers=8, n_days=3, seed=42)
    assert len(a) == len(b)
    assert all(x == y for x, y in zip(a, b))


def test_simulator_different_seeds_differ():
    a = generate(n_riders=20, n_drivers=8, n_days=3, seed=1)
    b = generate(n_riders=20, n_drivers=8, n_days=3, seed=2)
    assert a != b


def test_simulator_one_request_per_trip():
    """Each trip_id has exactly one REQUEST event."""
    events = generate(n_riders=20, n_drivers=8, n_days=3, seed=7)
    requests = [e for e in events if e.kind is TripEventKind.REQUEST]
    assert len({r.trip_id for r in requests}) == len(requests)


def test_simulator_dropoff_has_fare_and_distance():
    """Every DROPOFF event has fare_vnd > 0 and distance_m > 0."""
    events = generate(n_riders=30, n_drivers=10, n_days=3, seed=2)
    dropoffs = [e for e in events if e.kind is TripEventKind.DROPOFF]
    assert all(d.fare_vnd > 0 for d in dropoffs)
    assert all(d.distance_m > 0 for d in dropoffs)


def test_simulator_stitchable():
    """All generated trips can be stitched without raising."""
    events = generate(n_riders=20, n_drivers=8, n_days=5, seed=5)
    trips = stitch(events)
    assert len(trips) > 0
    # Every completed trip has a non-empty dest district.
    assert all(t.dest_district for t in trips if t.is_completed)


def test_simulator_rejects_invalid_fractions():
    with pytest.raises(ValueError):
        generate(expire_fraction=2.0)
    with pytest.raises(ValueError):
        generate(expire_fraction=0.5, rider_cancel_fraction=0.6, driver_cancel_fraction=0.5)


def test_simulator_rejects_invalid_size():
    with pytest.raises(ValueError):
        generate(n_riders=0)
    with pytest.raises(ValueError):
        generate(n_days=0)


# ---------- CLI ---------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vntrip.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    out = _run_cli("info")
    assert out.returncode == 0
    assert "ride-share-trip-pipeline" in out.stdout


def test_cli_pipeline_simulate_stitch_fare_surge_shifts(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    trips_path = tmp_path / "trips.jsonl"
    fares_path = tmp_path / "fares.jsonl"
    r = _run_cli(
        "simulate",
        "--riders",
        "30",
        "--drivers",
        "10",
        "--days",
        "5",
        "--seed",
        "1",
        "--output",
        str(events_path),
    )
    assert r.returncode == 0, r.stderr
    r = _run_cli("stitch", "--input", str(events_path), "--output", str(trips_path), "--show", "5")
    assert r.returncode == 0, r.stderr
    assert trips_path.exists()
    r = _run_cli("fare", "--input", str(events_path), "--output", str(fares_path), "--show", "5")
    assert r.returncode == 0, r.stderr
    assert fares_path.exists()
    r = _run_cli("surge", "--input", str(events_path), "--show", "5")
    assert r.returncode == 0, r.stderr
    r = _run_cli("shifts", "--input", str(events_path), "--show", "5")
    assert r.returncode == 0, r.stderr


def test_cli_fraud_exit_2_when_findings(tmp_path: Path) -> None:
    """``fraud`` exits 2 when at least one finding is surfaced."""
    events_path = tmp_path / "events.jsonl"
    _run_cli(
        "simulate",
        "--riders",
        "50",
        "--drivers",
        "15",
        "--days",
        "5",
        "--seed",
        "11",
        "--output",
        str(events_path),
    )
    r = _run_cli("fraud", "--input", str(events_path), "--show", "5")
    assert r.returncode == 2
    assert "CANCEL_ABUSE" in r.stdout or "PHANTOM_TRIP" in r.stdout


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    _run_cli(
        "simulate",
        "--riders",
        "20",
        "--drivers",
        "8",
        "--days",
        "3",
        "--seed",
        "5",
        "--output",
        str(events_path),
    )
    r = _run_cli("summary", "--input", str(events_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "n_events" in payload
    assert "n_trips" in payload
    assert "events_by_kind" in payload
    assert payload["n_events"] > 0
