"""air-quality-iot-pipeline — VN PM/NO2/SO2/O3/CO sensor pipeline → QCVN-05 AQI."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "AQIBand": ("aqipipe.qcvn", "AQIBand"),
        "Alert": ("aqipipe.alerts", "Alert"),
        "AlertKind": ("aqipipe.alerts", "AlertKind"),
        "Pollutant": ("aqipipe.schema", "Pollutant"),
        "PollutantAQI": ("aqipipe.qcvn", "PollutantAQI"),
        "Reading": ("aqipipe.schema", "Reading"),
        "Station": ("aqipipe.schema", "Station"),
        "StationAQI": ("aqipipe.qcvn", "StationAQI"),
        "StationKind": ("aqipipe.schema", "StationKind"),
        "VN_TZ": ("aqipipe.schema", "VN_TZ"),
        "WindowAverage": ("aqipipe.schema", "WindowAverage"),
        "aggregate": ("aqipipe.aggregate", "aggregate"),
        "alert_from_dict": ("aqipipe.io_jsonl", "alert_from_dict"),
        "alert_to_dict": ("aqipipe.io_jsonl", "alert_to_dict"),
        "aqi_for": ("aqipipe.qcvn", "aqi_for"),
        "average_from_dict": ("aqipipe.io_jsonl", "average_from_dict"),
        "average_to_dict": ("aqipipe.io_jsonl", "average_to_dict"),
        "band_distribution": ("aqipipe.alerts", "band_distribution"),
        "band_for_aqi": ("aqipipe.qcvn", "band_for_aqi"),
        "dump_alerts": ("aqipipe.io_jsonl", "dump_alerts"),
        "dump_averages": ("aqipipe.io_jsonl", "dump_averages"),
        "dump_readings": ("aqipipe.io_jsonl", "dump_readings"),
        "dump_stations": ("aqipipe.io_jsonl", "dump_stations"),
        "find_public_alerts": ("aqipipe.alerts", "find_public_alerts"),
        "find_sensitive_alerts": ("aqipipe.alerts", "find_sensitive_alerts"),
        "generate": ("aqipipe.simulator", "generate"),
        "latest_per_station": ("aqipipe.aggregate", "latest_per_station"),
        "load_alerts": ("aqipipe.io_jsonl", "load_alerts"),
        "load_averages": ("aqipipe.io_jsonl", "load_averages"),
        "load_readings": ("aqipipe.io_jsonl", "load_readings"),
        "load_stations": ("aqipipe.io_jsonl", "load_stations"),
        "reading_from_dict": ("aqipipe.io_jsonl", "reading_from_dict"),
        "reading_to_dict": ("aqipipe.io_jsonl", "reading_to_dict"),
        "station_aqi": ("aqipipe.qcvn", "station_aqi"),
        "station_from_dict": ("aqipipe.io_jsonl", "station_from_dict"),
        "station_to_dict": ("aqipipe.io_jsonl", "station_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AQIBand",
    "Alert",
    "AlertKind",
    "Pollutant",
    "PollutantAQI",
    "Reading",
    "Station",
    "StationAQI",
    "StationKind",
    "VN_TZ",
    "WindowAverage",
    "__version__",
    "aggregate",
    "alert_from_dict",
    "alert_to_dict",
    "aqi_for",
    "average_from_dict",
    "average_to_dict",
    "band_distribution",
    "band_for_aqi",
    "dump_alerts",
    "dump_averages",
    "dump_readings",
    "dump_stations",
    "find_public_alerts",
    "find_sensitive_alerts",
    "generate",
    "latest_per_station",
    "load_alerts",
    "load_averages",
    "load_readings",
    "load_stations",
    "reading_from_dict",
    "reading_to_dict",
    "station_aqi",
    "station_from_dict",
    "station_to_dict",
]
