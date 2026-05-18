"""Type-checked JSONL codec for stations, readings, averages, alerts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from aqipipe.alerts import Alert, AlertKind
from aqipipe.qcvn import AQIBand
from aqipipe.schema import Pollutant, Reading, Station, StationKind, WindowAverage

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def station_to_dict(s: Station) -> dict[str, object]:
    return {
        "station_id": s.station_id,
        "name": s.name,
        "kind": s.kind.value,
        "province_code": s.province_code,
        "lat_x100000": s.lat_x100000,
        "lon_x100000": s.lon_x100000,
    }


def station_from_dict(d: dict[str, object]) -> Station:
    return Station(
        station_id=_require_str(d, "station_id"),
        name=_require_str(d, "name"),
        kind=StationKind(_require_str(d, "kind")),
        province_code=_require_str(d, "province_code"),
        lat_x100000=_require_int(d, "lat_x100000"),
        lon_x100000=_require_int(d, "lon_x100000"),
    )


def reading_to_dict(r: Reading) -> dict[str, object]:
    return {
        "station_id": r.station_id,
        "pollutant": r.pollutant.value,
        "value_x10": r.value_x10,
        "observed_at": r.observed_at.isoformat(),
        "quality": r.quality,
    }


def reading_from_dict(d: dict[str, object]) -> Reading:
    return Reading(
        station_id=_require_str(d, "station_id"),
        pollutant=Pollutant(_require_str(d, "pollutant")),
        value_x10=_require_int(d, "value_x10"),
        observed_at=datetime.fromisoformat(_require_str(d, "observed_at")),
        quality=_require_str(d, "quality"),
    )


def average_to_dict(w: WindowAverage) -> dict[str, object]:
    return {
        "station_id": w.station_id,
        "pollutant": w.pollutant.value,
        "window_start": w.window_start.isoformat(),
        "window_end": w.window_end.isoformat(),
        "value_x10": w.value_x10,
        "n_samples": w.n_samples,
    }


def average_from_dict(d: dict[str, object]) -> WindowAverage:
    return WindowAverage(
        station_id=_require_str(d, "station_id"),
        pollutant=Pollutant(_require_str(d, "pollutant")),
        window_start=datetime.fromisoformat(_require_str(d, "window_start")),
        window_end=datetime.fromisoformat(_require_str(d, "window_end")),
        value_x10=_require_int(d, "value_x10"),
        n_samples=_require_int(d, "n_samples"),
    )


def alert_to_dict(a: Alert) -> dict[str, object]:
    return {
        "kind": a.kind.value,
        "station_id": a.station_id,
        "aqi": a.aqi,
        "band": a.band.value,
        "detected_at": a.detected_at.isoformat(),
        "detail": a.detail,
    }


def alert_from_dict(d: dict[str, object]) -> Alert:
    return Alert(
        kind=AlertKind(_require_str(d, "kind")),
        station_id=_require_str(d, "station_id"),
        aqi=_require_int(d, "aqi"),
        band=AQIBand(_require_str(d, "band")),
        detected_at=datetime.fromisoformat(_require_str(d, "detected_at")),
        detail=_require_str(d, "detail"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_stations(stations: Iterable[Station]) -> str:
    return _dump(station_to_dict(s) for s in stations)


def dump_readings(readings: Iterable[Reading]) -> str:
    return _dump(reading_to_dict(r) for r in readings)


def dump_averages(averages: Iterable[WindowAverage]) -> str:
    return _dump(average_to_dict(w) for w in averages)


def dump_alerts(alerts: Iterable[Alert]) -> str:
    return _dump(alert_to_dict(a) for a in alerts)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_stations(text: str) -> Iterator[Station]:
    for d in _iter_lines(text):
        yield station_from_dict(d)


def load_readings(text: str) -> Iterator[Reading]:
    for d in _iter_lines(text):
        yield reading_from_dict(d)


def load_averages(text: str) -> Iterator[WindowAverage]:
    for d in _iter_lines(text):
        yield average_from_dict(d)


def load_alerts(text: str) -> Iterator[Alert]:
    for d in _iter_lines(text):
        yield alert_from_dict(d)


__all__ = [
    "alert_from_dict",
    "alert_to_dict",
    "average_from_dict",
    "average_to_dict",
    "dump_alerts",
    "dump_averages",
    "dump_readings",
    "dump_stations",
    "load_alerts",
    "load_averages",
    "load_readings",
    "load_stations",
    "reading_from_dict",
    "reading_to_dict",
    "station_from_dict",
    "station_to_dict",
]
