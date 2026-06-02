"""Aggregator: out-of-order, gaps, window boundaries."""

from __future__ import annotations

from datetime import timedelta

import pytest

from aqipipe.aggregate import aggregate, latest_per_station
from aqipipe.schema import Pollutant

from ._fixtures import DEFAULT_TS, make_reading


def test_aggregate_rejects_unknown_window():
    with pytest.raises(ValueError):
        aggregate([], window="5m")


def test_single_reading_one_window():
    """One reading → one window of n=1."""
    [w] = aggregate([make_reading()], window="1h")
    assert w.n_samples == 1
    assert w.value_x10 == 500


def test_multiple_readings_in_same_window_average():
    readings = [
        make_reading(value_x10=400, observed_at=DEFAULT_TS + timedelta(minutes=5)),
        make_reading(value_x10=500, observed_at=DEFAULT_TS + timedelta(minutes=20)),
        make_reading(value_x10=600, observed_at=DEFAULT_TS + timedelta(minutes=45)),
    ]
    [w] = aggregate(readings, window="1h")
    assert w.n_samples == 3
    assert w.value_x10 == 500  # (400 + 500 + 600) / 3


def test_separate_pollutants_separate_windows():
    readings = [
        make_reading(pollutant=Pollutant.PM25, value_x10=500),
        make_reading(pollutant=Pollutant.NO2, value_x10=1000),
    ]
    out = aggregate(readings, window="1h")
    assert len(out) == 2
    pollutants = {w.pollutant for w in out}
    assert pollutants == {Pollutant.PM25, Pollutant.NO2}


def test_separate_stations_separate_windows():
    readings = [
        make_reading(station_id="AQ-001", value_x10=400),
        make_reading(station_id="AQ-002", value_x10=600),
    ]
    out = aggregate(readings, window="1h")
    assert len(out) == 2


def test_calibrating_readings_excluded():
    readings = [
        make_reading(value_x10=400, quality="CALIBRATING"),
        make_reading(value_x10=500, observed_at=DEFAULT_TS + timedelta(minutes=15)),
    ]
    [w] = aggregate(readings, window="1h")
    # Only the GOOD reading contributed.
    assert w.n_samples == 1
    assert w.value_x10 == 500


def test_stale_readings_excluded():
    readings = [
        make_reading(value_x10=400, quality="STALE"),
        make_reading(value_x10=500, observed_at=DEFAULT_TS + timedelta(minutes=15)),
    ]
    [w] = aggregate(readings, window="1h")
    assert w.n_samples == 1


def test_out_of_order_input_bucketed_correctly():
    """Shuffled input still buckets to the right window."""
    readings = [
        make_reading(value_x10=800, observed_at=DEFAULT_TS + timedelta(minutes=70)),
        make_reading(value_x10=200, observed_at=DEFAULT_TS + timedelta(minutes=10)),
        make_reading(value_x10=400, observed_at=DEFAULT_TS + timedelta(minutes=80)),
        make_reading(value_x10=600, observed_at=DEFAULT_TS + timedelta(minutes=30)),
    ]
    out = aggregate(readings, window="1h")
    assert len(out) == 2  # two 1-h windows
    # First window (DEFAULT_TS hour) has 200 + 600 → mean 400.
    # Second window has 800 + 400 → mean 600.
    out.sort(key=lambda w: w.window_start)
    assert out[0].value_x10 == 400
    assert out[1].value_x10 == 600


def test_1h_window_aligned_to_hour_boundary():
    """A reading at HH:42 buckets into the HH:00 — HH:59 window."""
    r = make_reading(observed_at=DEFAULT_TS + timedelta(minutes=42))
    [w] = aggregate([r], window="1h")
    assert w.window_start.minute == 0
    assert w.window_start.hour == DEFAULT_TS.hour


def test_24h_window_floors_to_midnight_vn():
    """24-h windows start at 00:00 VN, not UTC midnight."""
    r = make_reading(observed_at=DEFAULT_TS + timedelta(hours=4))
    [w] = aggregate([r], window="24h")
    assert w.window_start.hour == 0
    assert w.window_start.minute == 0


def test_8h_window_seconds_correct():
    out = aggregate([make_reading()], window="8h")
    assert (out[0].window_end - out[0].window_start) == timedelta(hours=8)


def test_latest_per_station_picks_most_recent():
    early = make_reading(value_x10=200, observed_at=DEFAULT_TS)
    late = make_reading(value_x10=800, observed_at=DEFAULT_TS + timedelta(hours=5))
    averages = aggregate([early, late], window="1h")
    latest = latest_per_station(averages)
    assert latest["AQ-00001"][Pollutant.PM25].value_x10 == 800


def test_empty_input_empty_output():
    assert aggregate([], window="1h") == []
