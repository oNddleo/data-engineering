"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logietr.cli import main
from logietr.schema import ShipmentState
from logietr.simulator import generate
from logietr.tracker import apply_events


def test_simulate_returns_coherent_streams():
    shipments, events = generate(n_shipments=20, seed=1)
    ship_ids = {s.shipment_id for s in shipments}
    # Every event references a real shipment.
    for ev in events:
        assert ev.shipment_id in ship_ids


def test_simulate_deterministic_with_same_seed():
    a = generate(n_shipments=15, seed=42)
    b = generate(n_shipments=15, seed=42)
    assert [s.shipment_id for s in a[0]] == [s.shipment_id for s in b[0]]
    assert len(a[1]) == len(b[1])


def test_simulate_pending_fraction_leaves_in_flight_shipments():
    shipments, events = generate(n_shipments=200, pending_fraction=0.5, failure_rate=0.0, seed=3)
    statuses = apply_events(shipments, events)
    n_terminal = sum(1 for s in statuses.values() if s.is_terminal)
    n_pending = sum(1 for s in statuses.values() if not s.is_terminal)
    assert n_pending > 0
    assert n_terminal > 0


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_shipments=0)
    with pytest.raises(ValueError):
        generate(failure_rate=1.5)
    with pytest.raises(ValueError):
        generate(pending_fraction=-0.1)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "logistics-eta-tracker" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(["simulate", "--n", "80", "--seed", "0", "--out-dir", str(out_dir)])
    assert rc == 0
    assert (out_dir / "shipments.jsonl").is_file()
    assert (out_dir / "events.jsonl").is_file()
    capsys.readouterr()

    rc = main(["status", "--in-dir", str(out_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DELIVERED" in out

    rc = main(["eta", "--in-dir", str(out_dir), "--n", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "shipment" in out

    rc = main(["breaches", "--in-dir", str(out_dir), "--n", "5", "--stuck-hours", "12"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OVERDUE" in out and "STUCK" in out

    rc = main(["carriers", "--in-dir", str(out_dir), "--min-volume", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "carrier" in out

    rc = main(["summary", "--in-dir", str(out_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_shipments"] == 80
    assert "by_state" in payload


def test_simulate_failure_rate_drives_failed_shipments():
    shipments, events = generate(n_shipments=200, failure_rate=1.0, pending_fraction=0.0, seed=4)
    statuses = apply_events(shipments, events)
    n_returned = sum(1 for s in statuses.values() if s.state is ShipmentState.RETURNED)
    # With failure_rate=1.0 and pending_fraction=0, all should reach RETURNED.
    assert n_returned == len(shipments)


def test_simulate_no_failures_all_delivered():
    shipments, events = generate(n_shipments=100, failure_rate=0.0, pending_fraction=0.0, seed=5)
    statuses = apply_events(shipments, events)
    n_delivered = sum(1 for s in statuses.values() if s.state is ShipmentState.DELIVERED)
    assert n_delivered == len(shipments)
