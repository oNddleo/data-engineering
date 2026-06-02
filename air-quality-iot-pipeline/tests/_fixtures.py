"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aqipipe.schema import VN_TZ, Pollutant, Reading, Station, StationKind, WindowAverage

DEFAULT_TS = datetime(2026, 5, 17, 9, 0, 0, tzinfo=VN_TZ)


def make_station(**overrides: Any) -> Station:
    defaults = {
        "station_id": "AQ-00001",
        "name": "Hà Nội station 1",
        "kind": StationKind.STATE,
        "province_code": "HN",
        "lat_x100000": 2102800,
        "lon_x100000": 10584180,
    }
    defaults.update(overrides)
    return Station(**defaults)  # type: ignore[arg-type]


def make_reading(**overrides: Any) -> Reading:
    defaults = {
        "station_id": "AQ-00001",
        "pollutant": Pollutant.PM25,
        "value_x10": 500,
        "observed_at": DEFAULT_TS,
        "quality": "GOOD",
    }
    defaults.update(overrides)
    return Reading(**defaults)  # type: ignore[arg-type]


def make_average(**overrides: Any) -> WindowAverage:
    defaults = {
        "station_id": "AQ-00001",
        "pollutant": Pollutant.PM25,
        "window_start": DEFAULT_TS,
        "window_end": DEFAULT_TS + timedelta(hours=1),
        "value_x10": 500,
        "n_samples": 4,
    }
    defaults.update(overrides)
    return WindowAverage(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_average", "make_reading", "make_station"]
