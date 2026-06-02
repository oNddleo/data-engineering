"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cartrec.cli import main
from cartrec.detect import find_abandoned
from cartrec.sessionize import sessionize
from cartrec.simulator import generate


def test_simulate_deterministic():
    a = generate(n_buyers=20, seed=42)
    b = generate(n_buyers=20, seed=42)
    assert [e.event_id for e in a] == [e.event_id for e in b]


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_buyers=0)
    with pytest.raises(ValueError):
        generate(recovery_fraction=1.5)


def test_simulator_to_sessionize_pipeline():
    events = generate(n_buyers=30, seed=1)
    sessions = sessionize(events)
    assert len(sessions) >= 1
    # Each session has >= 1 event.
    assert all(s.n_events >= 1 for s in sessions)


def test_simulator_produces_carting_sessions():
    """With > 0 buyers and the default archetype mix, we'll see carting + completed sessions."""
    events = generate(n_buyers=50, seed=2)
    sessions = sessionize(events)
    n_completed = sum(1 for s in sessions if s.completed_checkout)
    n_carting = sum(1 for s in sessions if s.n_add > 0)
    assert n_completed > 0
    assert n_carting > n_completed  # not all carting sessions complete


def test_simulator_recovery_path():
    """With recovery_fraction=1.0, every abandoner converts within window."""
    events = generate(n_buyers=50, recovery_fraction=1.0, seed=3)
    # Each abandoner gets an extra COMPLETE_CHECKOUT injected after the
    # abandon timestamp — verify the event count grew.
    events_no_recovery = generate(n_buyers=50, recovery_fraction=0.0, seed=3)
    assert len(events) > len(events_no_recovery)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "abandoned-cart-recovery-pipeline" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events_path = tmp_path / "events.jsonl"
    rc = main(["simulate", "--buyers", "50", "--seed", "0", "--output", str(events_path)])
    assert rc == 0
    capsys.readouterr()

    sessions_path = tmp_path / "sessions.jsonl"
    rc = main(["sessionize", "--input", str(events_path), "--output", str(sessions_path)])
    assert rc == 0
    capsys.readouterr()

    rc = main(["detect", "--input", str(sessions_path), "--show", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Abandon rate" in out

    touches_path = tmp_path / "touches.jsonl"
    rc = main(["schedule", "--input", str(sessions_path), "--output", str(touches_path)])
    assert rc == 0
    capsys.readouterr()

    rc = main(
        [
            "attribute",
            "--touches",
            str(touches_path),
            "--events",
            str(events_path),
            "--window-hours",
            "24",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Conversion rate" in out

    rc = main(["summary", "--input", str(sessions_path)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "n_sessions" in payload
    assert "n_abandoned" in payload


def test_simulator_sessions_round_trip_through_detect():
    """A full simulate → sessionize → detect run produces some abandoned sessions."""
    events = generate(n_buyers=100, seed=4)
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions)
    assert len(abandoned) > 0
