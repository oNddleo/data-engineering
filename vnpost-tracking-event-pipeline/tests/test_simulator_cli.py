"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vnpost.schema import ParcelEventKind
from vnpost.simulator import generate
from vnpost.state import stitch


def test_simulator_deterministic():
    a = generate(n_parcels=20, seed=42)
    b = generate(n_parcels=20, seed=42)
    assert a == b


def test_simulator_different_seeds_differ():
    a = generate(n_parcels=20, seed=1)
    b = generate(n_parcels=20, seed=2)
    assert a != b


def test_simulator_emits_request_per_parcel():
    """Each parcel gets at least 2 scans."""
    events = generate(n_parcels=30, seed=7)
    by_tracking: dict[str, int] = {}
    for e in events:
        by_tracking[e.tracking_id] = by_tracking.get(e.tracking_id, 0) + 1
    assert all(c >= 2 for c in by_tracking.values())


def test_simulator_output_stitchable():
    """All generated parcels stitch without error."""
    events = generate(n_parcels=50, seed=5)
    parcels = stitch(events)
    assert len(parcels) == 50


def test_simulator_rejects_invalid_args():
    with pytest.raises(ValueError):
        generate(n_parcels=-1)
    with pytest.raises(ValueError):
        generate(delivered_fraction=1.5)
    with pytest.raises(ValueError):
        generate(
            delivered_fraction=0.5,
            late_fraction=0.4,
            returned_fraction=0.4,
        )


def test_simulator_dropoff_count():
    """A reasonable fraction of parcels get DELIVERED."""
    events = generate(n_parcels=200, seed=11)
    delivered = sum(1 for e in events if e.kind is ParcelEventKind.DELIVERED)
    # Approx 80% + 8% + 2% + 3% = 93% should deliver
    assert delivered >= 150


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vnpost.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    r = _run_cli("info")
    assert r.returncode == 0
    assert "vnpost-tracking-event-pipeline" in r.stdout


def test_cli_full_pipeline(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    parcels_path = tmp_path / "parcels.jsonl"
    r = _run_cli("simulate", "--parcels", "50", "--seed", "1", "--output", str(events_path))
    assert r.returncode == 0, r.stderr
    r = _run_cli(
        "stitch", "--input", str(events_path), "--output", str(parcels_path), "--show", "3"
    )
    assert r.returncode == 0, r.stderr
    r = _run_cli("sla", "--input", str(events_path))
    assert r.returncode == 0, r.stderr
    assert "on-time%" in r.stdout


def test_cli_fraud_exit_code_2_when_findings(tmp_path: Path) -> None:
    """fraud command exits 2 when any finding is surfaced."""
    events_path = tmp_path / "events.jsonl"
    _run_cli("simulate", "--parcels", "300", "--seed", "7", "--output", str(events_path))
    r = _run_cli("fraud", "--input", str(events_path), "--show", "3")
    # At ~3% scan-skip + ~3% abnormal-dwell, 300 parcels yields findings.
    assert r.returncode == 2


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    _run_cli("simulate", "--parcels", "50", "--seed", "1", "--output", str(events_path))
    r = _run_cli("summary", "--input", str(events_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_parcels"] == 50
    assert "by_courier" in payload
