"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from aqipipe.alerts import Alert, AlertKind
from aqipipe.io_jsonl import (
    alert_from_dict,
    dump_alerts,
    dump_averages,
    dump_readings,
    dump_stations,
    load_alerts,
    load_averages,
    load_readings,
    load_stations,
    reading_from_dict,
    station_from_dict,
)
from aqipipe.qcvn import AQIBand
from aqipipe.schema import VN_TZ

from ._fixtures import DEFAULT_TS, make_average, make_reading, make_station


def test_station_roundtrip():
    s = make_station()
    [back] = list(load_stations(dump_stations([s])))
    assert back == s


def test_reading_roundtrip():
    r = make_reading()
    [back] = list(load_readings(dump_readings([r])))
    assert back == r


def test_average_roundtrip():
    a = make_average()
    [back] = list(load_averages(dump_averages([a])))
    assert back == a


def test_alert_roundtrip():
    alert = Alert(
        kind=AlertKind.PUBLIC,
        station_id="AQ-001",
        aqi=180,
        band=AQIBand.UNHEALTHY,
        detected_at=DEFAULT_TS,
        detail="test",
    )
    [back] = list(load_alerts(dump_alerts([alert])))
    assert back == alert


def test_reading_decoder_rejects_unknown_pollutant():
    bad = {
        "station_id": "AQ-001",
        "pollutant": "RADON",
        "value_x10": 100,
        "observed_at": "2026-05-17T09:00:00+07:00",
        "quality": "GOOD",
    }
    with pytest.raises(ValueError):
        reading_from_dict(bad)


def test_station_decoder_rejects_unknown_kind():
    bad = {
        "station_id": "AQ-001",
        "name": "x",
        "kind": "GHOST",
        "province_code": "HN",
        "lat_x100000": 2102800,
        "lon_x100000": 10584180,
    }
    with pytest.raises(ValueError):
        station_from_dict(bad)


def test_reading_decoder_rejects_bool_for_int():
    bad = {
        "station_id": "AQ-001",
        "pollutant": "PM25",
        "value_x10": True,
        "observed_at": "2026-05-17T09:00:00+07:00",
        "quality": "GOOD",
    }
    with pytest.raises(TypeError, match="value_x10"):
        reading_from_dict(bad)


def test_alert_decoder_rejects_unknown_band():
    bad = {
        "kind": "PUBLIC",
        "station_id": "AQ-001",
        "aqi": 180,
        "band": "TOXIC",
        "detected_at": "2026-05-17T09:00:00+07:00",
        "detail": "x",
    }
    with pytest.raises(ValueError):
        alert_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_readings([make_reading()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_readings(padded))) == 1


def test_multi_record_roundtrip():
    readings = [
        make_reading(value_x10=v, observed_at=DEFAULT_TS + timedelta(minutes=5 * i))
        for i, v in enumerate([100, 200, 300, 400, 500])
    ]
    text = dump_readings(readings)
    assert list(load_readings(text)) == readings


def test_average_decoder_window_dates_roundtrip():
    a = make_average(
        window_start=datetime(2026, 5, 17, 0, 0, tzinfo=VN_TZ),
        window_end=datetime(2026, 5, 17, 1, 0, tzinfo=VN_TZ),
    )
    [back] = list(load_averages(dump_averages([a])))
    assert back.window_start == a.window_start
    assert back.window_end == a.window_end
