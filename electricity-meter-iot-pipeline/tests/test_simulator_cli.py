"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evnmeter.cli import main
from evnmeter.derive import derive
from evnmeter.simulator import generate


def test_simulate_deterministic():
    a = generate(n_meters=5, n_days=2, seed=42)
    b = generate(n_meters=5, n_days=2, seed=42)
    assert [m.meter_id for m in a[0]] == [m.meter_id for m in b[0]]
    assert len(a[1]) == len(b[1])


def test_simulate_emits_expected_count():
    meters, readings = generate(
        n_meters=4, n_days=2, gap_fraction=0.0, out_of_order_fraction=0.0, seed=1
    )
    # 4 meters × 2 days × (24×60/30=48 intervals/day) = 384 readings.
    assert len(meters) == 4
    assert len(readings) == 4 * 2 * 48


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_meters=0)
    with pytest.raises(ValueError):
        generate(n_days=0)
    with pytest.raises(ValueError):
        generate(gap_fraction=1.5)


def test_simulate_to_derive_pipeline():
    """Simulator output is valid input for the derive pass."""
    _, readings = generate(n_meters=3, n_days=2, seed=2)
    intervals = derive(readings)
    assert len(intervals) > 0


def test_simulate_rollover_exercised():
    """``rollover_fraction=1.0`` puts every meter near the rollover threshold."""
    _, readings = generate(
        n_meters=3,
        n_days=2,
        rollover_fraction=1.0,
        gap_fraction=0.0,
        out_of_order_fraction=0.0,
        seed=4,
    )
    intervals = derive(readings)
    # The derive pass either produces normal intervals (deltas wrap correctly)
    # or zero intervals if every wrap is detected as a fault.
    # We just verify no negative deltas leak through.
    assert all(c.kwh_x100 >= 0 for c in intervals)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "electricity-meter-iot-pipeline" in out


def test_cli_quote_350(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["quote", "350"])
    out = capsys.readouterr().out
    assert rc == 0
    # The example total from the README docstring.
    assert "891,756" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(
        ["simulate", "--meters", "5", "--days", "3", "--seed", "0", "--out-dir", str(out_dir)]
    )
    assert rc == 0
    assert (out_dir / "meters.jsonl").is_file()
    assert (out_dir / "readings.jsonl").is_file()
    capsys.readouterr()

    intervals_path = tmp_path / "intervals.jsonl"
    rc = main(
        ["derive", "--input", str(out_dir / "readings.jsonl"), "--output", str(intervals_path)]
    )
    assert rc == 0
    capsys.readouterr()

    rc = main(["anomaly", "--input", str(intervals_path), "--show", "2"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "GAPS" in out
    assert "SPIKES" in out
    assert "STUCK" in out

    bills_path = tmp_path / "bills.jsonl"
    rc = main(
        [
            "bill",
            "--input",
            str(intervals_path),
            "--period-start",
            "2026-05-01T00:00:00+07:00",
            "--period-end",
            "2026-05-04T00:00:00+07:00",
            "--output",
            str(bills_path),
            "--show",
            "3",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = main(["summary", "--input", str(intervals_path)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_meters"] == 5
    assert "per_meter" in payload
