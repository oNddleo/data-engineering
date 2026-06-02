"""Seeded synthetic air-quality telemetry.

Mimics a VN region with both STATE and PRIVATE stations. Realism touches:

* **Diurnal NO2 / PM curve** — bias toward 07:00 – 09:00 morning rush
  and 17:00 – 19:00 evening, plus a midnight uptick from cooking smoke
  in residential districts.
* **Province baselines** — Hanoi runs higher PM2.5 than Đà Nẵng on
  average (the geography is real).
* **Calibration drift** — PRIVATE stations get ``CALIBRATING`` quality
  on ~3% of readings.
* **Out-of-order arrival** — ~5% of readings get shuffled with an
  adjacent slot to exercise the aggregator's resort step.
* **Stuck-readings** — 1% of stations report the same value 10× in a
  row (the classic broken-sensor pattern).
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from aqipipe.schema import VN_TZ, Pollutant, Reading, Station, StationKind

_DEFAULT_BASE_TS = datetime(2026, 5, 17, 0, 0, 0, tzinfo=VN_TZ)


# Real VN provinces + plausible city-centre coordinates × 100_000.
_PROVINCES: tuple[tuple[str, str, int, int], ...] = (
    # province_code, name, lat_x100000, lon_x100000
    ("HN", "Hà Nội", 2102800, 10584180),  # Hoàn Kiếm
    ("HCMC", "TP HCM", 1077200, 10669940),  # District 1
    ("DN", "Đà Nẵng", 1604200, 10821940),  # Hải Châu
    ("HP", "Hải Phòng", 2086200, 10668500),  # Lê Chân
    ("CT", "Cần Thơ", 1003770, 10579330),  # Ninh Kiều
    ("HUE", "Huế", 1646080, 10759770),
    ("QN", "Quảng Nam", 1557420, 10848890),
    ("BD", "Bình Dương", 1098490, 10665230),
)


# Per-province pollutant baselines (µg/m³ for PM/NO2/SO2/O3, mg/m³ for CO).
# Hanoi PM2.5 routinely > 50 (Unhealthy band); HCMC ~ 35 (Moderate).
_BASELINES_X10: dict[str, dict[Pollutant, int]] = {
    "HN": {
        Pollutant.PM25: 600,
        Pollutant.PM10: 1200,
        Pollutant.NO2: 800,
        Pollutant.SO2: 200,
        Pollutant.O3: 900,
        Pollutant.CO: 80,
    },
    "HCMC": {
        Pollutant.PM25: 400,
        Pollutant.PM10: 850,
        Pollutant.NO2: 900,
        Pollutant.SO2: 250,
        Pollutant.O3: 1100,
        Pollutant.CO: 90,
    },
    "DN": {
        Pollutant.PM25: 250,
        Pollutant.PM10: 600,
        Pollutant.NO2: 400,
        Pollutant.SO2: 150,
        Pollutant.O3: 800,
        Pollutant.CO: 50,
    },
    "HP": {
        Pollutant.PM25: 500,
        Pollutant.PM10: 1000,
        Pollutant.NO2: 700,
        Pollutant.SO2: 280,
        Pollutant.O3: 850,
        Pollutant.CO: 70,
    },
    "CT": {
        Pollutant.PM25: 300,
        Pollutant.PM10: 700,
        Pollutant.NO2: 500,
        Pollutant.SO2: 180,
        Pollutant.O3: 900,
        Pollutant.CO: 60,
    },
    "HUE": {
        Pollutant.PM25: 220,
        Pollutant.PM10: 550,
        Pollutant.NO2: 350,
        Pollutant.SO2: 120,
        Pollutant.O3: 780,
        Pollutant.CO: 40,
    },
    "QN": {
        Pollutant.PM25: 280,
        Pollutant.PM10: 650,
        Pollutant.NO2: 450,
        Pollutant.SO2: 160,
        Pollutant.O3: 820,
        Pollutant.CO: 55,
    },
    "BD": {
        Pollutant.PM25: 450,
        Pollutant.PM10: 900,
        Pollutant.NO2: 850,
        Pollutant.SO2: 270,
        Pollutant.O3: 1000,
        Pollutant.CO: 75,
    },
}


def _diurnal_factor(hour: int, pollutant: Pollutant) -> float:
    """Time-of-day multiplier per pollutant."""
    if pollutant in (Pollutant.NO2, Pollutant.CO):
        # Bimodal traffic peak.
        morning = math.cos((hour - 8) * math.pi / 6) ** 2
        evening = math.cos((hour - 18) * math.pi / 6) ** 2
        return 0.4 + 0.6 * max(morning, evening)
    if pollutant is Pollutant.O3:
        # O3 peaks at midday due to photochemistry.
        return 0.3 + 0.7 * max(0.0, math.cos((hour - 13) * math.pi / 8) ** 2)
    if pollutant in (Pollutant.PM25, Pollutant.PM10):
        # Cooking smoke 06:00 / 12:00 / 18:00 plus mild rush peaks.
        cooking = max(
            math.cos((hour - 6) * math.pi / 4) ** 2,
            math.cos((hour - 12) * math.pi / 4) ** 2,
            math.cos((hour - 18) * math.pi / 4) ** 2,
        )
        return 0.5 + 0.5 * cooking
    # SO2 — fairly flat industrial baseline.
    return 0.8 + 0.2 * (math.cos((hour - 10) * math.pi / 12) ** 2)


def generate(
    *,
    n_stations: int = 10,
    n_hours: int = 24,
    interval_minutes: int = 15,
    private_fraction: float = 0.4,
    drift_fraction: float = 0.03,
    out_of_order_fraction: float = 0.05,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Station], list[Reading]]:
    """Generate stations + readings over ``n_hours``."""
    if n_stations < 1:
        raise ValueError("n_stations must be >= 1")
    if n_hours < 1:
        raise ValueError("n_hours must be >= 1")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be > 0")
    for name, val in (
        ("private_fraction", private_fraction),
        ("drift_fraction", drift_fraction),
        ("out_of_order_fraction", out_of_order_fraction),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    stations: list[Station] = []
    for i in range(n_stations):
        prov_code, prov_name, lat, lon = rng.choice(_PROVINCES)
        kind = StationKind.PRIVATE if rng.random() < private_fraction else StationKind.STATE
        # Add ~1km jitter on coordinates.
        lat_j = lat + rng.randint(-1000, 1000)
        lon_j = lon + rng.randint(-1000, 1000)
        stations.append(
            Station(
                station_id=f"AQ-{i:05d}",
                name=f"{prov_name} station {i}",
                kind=kind,
                province_code=prov_code,
                lat_x100000=lat_j,
                lon_x100000=lon_j,
            )
        )

    readings: list[Reading] = []
    n_intervals = n_hours * (60 // interval_minutes)
    pollutants = list(Pollutant)
    for st in stations:
        baseline = _BASELINES_X10[st.province_code]
        for k in range(n_intervals):
            ts = base + timedelta(minutes=k * interval_minutes)
            hour = ts.hour
            for poll in pollutants:
                factor = _diurnal_factor(hour, poll)
                # Mild log-normal noise around the baseline × factor.
                noise = rng.gauss(0, 0.15)
                value = baseline[poll] * factor * math.exp(noise)
                # Clamp & truncate to int.
                value_x10 = max(0, int(value + 0.5))
                quality = "GOOD"
                if st.kind is StationKind.PRIVATE and rng.random() < drift_fraction:
                    quality = "CALIBRATING"
                readings.append(
                    Reading(
                        station_id=st.station_id,
                        pollutant=poll,
                        value_x10=value_x10,
                        observed_at=ts,
                        quality=quality,
                    )
                )

    # Shuffle adjacent pairs to simulate out-of-order arrival.
    for i in range(len(readings) - 1):
        if rng.random() < out_of_order_fraction:
            readings[i], readings[i + 1] = readings[i + 1], readings[i]

    return stations, readings


__all__ = ["generate"]
