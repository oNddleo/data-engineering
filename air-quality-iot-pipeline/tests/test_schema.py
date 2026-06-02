"""Schema invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from aqipipe.schema import VN_TZ, Pollutant, StationKind

from ._fixtures import DEFAULT_TS, make_average, make_reading, make_station


def test_vn_tz_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_pollutant_enum_six_values():
    assert {p.value for p in Pollutant} == {"PM25", "PM10", "NO2", "SO2", "O3", "CO"}


def test_station_kind_enum():
    assert {k.value for k in StationKind} == {"STATE", "PRIVATE"}


def test_station_validates_vn_bounding_box():
    # Latitude outside VN range (too far south, below 8°N).
    with pytest.raises(ValueError, match="lat"):
        make_station(lat_x100000=700_000)
    # Longitude outside VN (too far east).
    with pytest.raises(ValueError, match="lon"):
        make_station(lon_x100000=12_000_000)


def test_station_rejects_empty_id():
    with pytest.raises(ValueError):
        make_station(station_id="")


def test_station_rejects_empty_name():
    with pytest.raises(ValueError):
        make_station(name="")


def test_station_rejects_empty_province():
    with pytest.raises(ValueError):
        make_station(province_code="")


def test_reading_rejects_negative_value():
    with pytest.raises(ValueError):
        make_reading(value_x10=-1)


def test_reading_zero_value_is_legal():
    """Zero concentration is a valid reading — pristine air exists."""
    r = make_reading(value_x10=0)
    assert r.value_x10 == 0


def test_reading_rejects_naive_observed_at():
    with pytest.raises(ValueError):
        make_reading(observed_at=datetime(2026, 5, 17, 9, 0))


def test_reading_rejects_invalid_quality():
    with pytest.raises(ValueError):
        make_reading(quality="WEIRD")


def test_reading_accepts_calibrating_quality():
    r = make_reading(quality="CALIBRATING")
    assert r.quality == "CALIBRATING"


def test_average_rejects_window_start_after_end():
    with pytest.raises(ValueError):
        make_average(
            window_start=DEFAULT_TS + timedelta(hours=1),
            window_end=DEFAULT_TS,
        )


def test_average_rejects_zero_samples():
    with pytest.raises(ValueError):
        make_average(n_samples=0)


def test_average_rejects_negative_value():
    with pytest.raises(ValueError):
        make_average(value_x10=-1)


def test_station_accepts_lat_lon_at_vn_boundary():
    """Latitude 8.0°N and longitude 102.0°E are at the VN boundary — legal."""
    s = make_station(lat_x100000=800_000, lon_x100000=10_200_000)
    assert s.lat_x100000 == 800_000
