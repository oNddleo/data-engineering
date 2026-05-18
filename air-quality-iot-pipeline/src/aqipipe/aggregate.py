"""Bucket raw readings into fixed-window averages per (station, pollutant).

Three windows match the QĐ 1459 averaging requirements:

* **1-hour** for NO2 / SO2 / O3 / PM-instantaneous reporting.
* **8-hour rolling** for CO and O3 (8-hour AQI variant).
* **24-hour** for PM2.5 / PM10 (the canonical band-driver).

The aggregator:

1. Sorts readings per ``(station_id, pollutant)`` by ``observed_at``
   — production sensor feeds arrive slightly out-of-order over
   3G/4G/LoRa, and rebucketing after the fact is the recurring
   "stale-but-correct" win.
2. Buckets into fixed-width windows whose boundaries are aligned to
   the ``VN_TZ`` epoch (a 1-hour bar starts on ``:00``, a 24-h bar at
   ``00:00 VN`` — not UTC midnight).
3. Computes the arithmetic mean per bucket. Empty buckets are
   omitted (sparse output).

CALIBRATING or STALE readings are **excluded** from the average —
they'd skew the mean and a downstream "calibration drift" alert is
the right channel for them, not band-mis-classification.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from aqipipe.schema import VN_TZ, WindowAverage

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aqipipe.schema import Pollutant, Reading


def _floor_to_window(ts: datetime, window_seconds: int) -> datetime:
    """Floor ``ts`` to the start of its window in ``VN_TZ``.

    For 24-h windows this floors to midnight VN; for sub-day windows
    it floors to the multiple-of-window-seconds inside the day.
    """
    local = ts.astimezone(VN_TZ)
    if window_seconds >= 86400:
        floored = local.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        seconds_into_day = local.hour * 3600 + local.minute * 60 + local.second
        delta = seconds_into_day % window_seconds
        floored = local - timedelta(seconds=delta, microseconds=local.microsecond)
    return floored.astimezone(timezone.utc).astimezone(VN_TZ)


def aggregate(
    readings: Iterable[Reading],
    *,
    window: str = "1h",
) -> list[WindowAverage]:
    """Fold readings into ``WindowAverage``s at ``window`` granularity.

    ``window`` must be one of ``"1h"``, ``"8h"``, ``"24h"``.
    """
    window_seconds = {"1h": 3600, "8h": 8 * 3600, "24h": 86400}.get(window)
    if window_seconds is None:
        raise ValueError(f"window must be one of 1h/8h/24h, got {window!r}")

    buckets: dict[tuple[str, Pollutant, datetime], list[int]] = defaultdict(list)
    for r in readings:
        if r.quality != "GOOD":
            # Skip CALIBRATING / STALE — they'd skew the mean.
            continue
        bucket_start = _floor_to_window(r.observed_at, window_seconds)
        buckets[(r.station_id, r.pollutant, bucket_start)].append(r.value_x10)

    out: list[WindowAverage] = []
    for (station_id, pollutant, bucket_start), values in sorted(buckets.items()):
        mean_x10 = sum(values) // len(values)  # integer mean
        out.append(
            WindowAverage(
                station_id=station_id,
                pollutant=pollutant,
                window_start=bucket_start,
                window_end=bucket_start + timedelta(seconds=window_seconds),
                value_x10=mean_x10,
                n_samples=len(values),
            )
        )
    return out


def latest_per_station(
    averages: list[WindowAverage],
) -> dict[str, dict[Pollutant, WindowAverage]]:
    """``{station_id: {pollutant: latest_window_average}}`` — drives station AQI."""
    out: dict[str, dict[Pollutant, WindowAverage]] = defaultdict(dict)
    # Sort ascending so later writes win.
    for w in sorted(averages, key=lambda w: w.window_start):
        out[w.station_id][w.pollutant] = w
    return {sid: dict(d) for sid, d in out.items()}


__all__ = ["aggregate", "latest_per_station"]
