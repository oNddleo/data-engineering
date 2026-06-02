"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aqipipe.aggregate import aggregate
from aqipipe.cli import main
from aqipipe.schema import Pollutant
from aqipipe.simulator import generate


def test_simulate_deterministic():
    a = generate(n_stations=5, n_hours=4, seed=42)
    b = generate(n_stations=5, n_hours=4, seed=42)
    assert [s.station_id for s in a[0]] == [s.station_id for s in b[0]]
    assert len(a[1]) == len(b[1])


def test_simulate_emits_six_pollutants_per_station():
    stations, readings = generate(n_stations=3, n_hours=2, interval_minutes=30, seed=1)
    # 3 stations × 2h × 2 intervals/h × 6 pollutants = 72 readings.
    assert len(readings) == 3 * 2 * 2 * 6
    pollutants = {r.pollutant for r in readings}
    assert pollutants == set(Pollutant)


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_stations=0)
    with pytest.raises(ValueError):
        generate(n_hours=0)
    with pytest.raises(ValueError):
        generate(drift_fraction=1.5)


def test_simulator_to_aggregate_pipeline():
    _, readings = generate(n_stations=2, n_hours=3, seed=2)
    averages = aggregate(readings, window="1h")
    assert len(averages) > 0
    for w in averages:
        assert w.value_x10 >= 0
        assert w.n_samples >= 1


def test_simulate_stations_in_vn_bounding_box():
    """All synthetic stations fall in the VN bounding box."""
    stations, _ = generate(n_stations=20, n_hours=1, seed=3)
    for s in stations:
        assert 800_000 <= s.lat_x100000 <= 2_400_000
        assert 10_200_000 <= s.lon_x100000 <= 11_000_000


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "air-quality-iot-pipeline" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(
        [
            "simulate",
            "--stations",
            "5",
            "--hours",
            "6",
            "--seed",
            "0",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "stations.jsonl").is_file()
    assert (out_dir / "readings.jsonl").is_file()
    capsys.readouterr()

    avg_path = tmp_path / "avg.jsonl"
    rc = main(
        [
            "aggregate",
            "--input",
            str(out_dir / "readings.jsonl"),
            "--window",
            "1h",
            "--output",
            str(avg_path),
        ]
    )
    assert rc == 0
    assert avg_path.is_file()
    capsys.readouterr()

    rc = main(["aqi", "--input", str(avg_path), "--n", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "station" in out

    rc = main(
        [
            "alerts",
            "--input",
            str(avg_path),
            "--min-band",
            "GOOD",
            "--show",
            "3",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Band distribution" in out

    rc = main(["quote", "PM25", "500"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["aqi"] == 100
    assert payload["band"] == "MODERATE"

    rc = main(["summary", "--input", str(out_dir / "readings.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_stations"] == 5
    assert set(payload["by_pollutant"]) == {"PM25", "PM10", "NO2", "SO2", "O3", "CO"}


def test_cli_quote_hazardous_pm25(capsys: pytest.CaptureFixture[str]) -> None:
    """Quote a hazardous PM2.5 — sanity check the boundary."""
    rc = main(["quote", "PM25", "5000"])  # 500 µg/m³
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["band"] == "HAZARDOUS"
