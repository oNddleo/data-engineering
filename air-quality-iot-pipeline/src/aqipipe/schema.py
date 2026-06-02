"""Air-quality sensor schema modelled on VN monitoring stations.

VN has two parallel networks:

* **State-operated**: Ministry of Natural Resources (Bộ TNMT) stations.
  ~30 nationwide, report every 15 minutes, methodology fixed by
  QCVN 05:2023/BTNMT.
* **PAM Air private network**: ~150 stations, report every 5 minutes,
  lower-grade sensors but much denser coverage. Calibration drift is
  a known issue.

The schema tolerates both: ``station_kind`` lets downstream code
weight readings appropriately. All concentrations are stored as
``int(value × 10)`` — one decimal place of precision is what every
VN AQI publication actually uses, and integer storage avoids the
float-drift bug that haunts environmental databases.

| Pollutant | Unit        | Averaging window |
| --------- | ----------- | ---------------- |
| PM2.5     | µg/m³       | 24 h or 1 h      |
| PM10      | µg/m³       | 24 h or 1 h      |
| NO2       | µg/m³       | 1 h              |
| SO2       | µg/m³       | 1 h              |
| CO        | mg/m³       | 8 h              |
| O3        | µg/m³       | 1 h or 8 h       |

CO is the odd one out — reported in **mg/m³** not µg/m³ — but for
schema uniformity we store its value × 10 like the others. The
breakpoint table in :mod:`aqipipe.qcvn` knows which units each
pollutant uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Pollutant(str, Enum):
    """The six pollutants AQI is computed from in VN methodology."""

    PM25 = "PM25"  # PM2.5 — fine particulate matter (µg/m³)
    PM10 = "PM10"  # PM10 — coarse particulate matter (µg/m³)
    NO2 = "NO2"  # Nitrogen dioxide (µg/m³)
    SO2 = "SO2"  # Sulfur dioxide (µg/m³)
    O3 = "O3"  # Ozone (µg/m³)
    CO = "CO"  # Carbon monoxide (mg/m³ — note unit)


class StationKind(str, Enum):
    """Two VN air-quality networks differ in cadence + calibration."""

    STATE = "STATE"  # Bộ TNMT — 15-min cadence, regulated calibration
    PRIVATE = "PRIVATE"  # PAM Air & friends — 5-min cadence, more drift


@dataclass(frozen=True, slots=True)
class Station:
    """Air-quality monitoring station."""

    station_id: str
    name: str
    kind: StationKind
    province_code: str  # "HN", "HCMC", "DN", "HP", "CT", "HUE", "QN", "BD"
    lat_x100000: int  # latitude × 100_000 (5 decimal places, ~1 m precision)
    lon_x100000: int  # longitude × 100_000

    def __post_init__(self) -> None:
        if not self.station_id:
            raise ValueError("station_id must be non-empty")
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.province_code:
            raise ValueError("province_code must be non-empty")
        # VN bounding box: roughly 8°N – 24°N, 102°E – 110°E.
        if not 800_000 <= self.lat_x100000 <= 2_400_000:
            raise ValueError(
                f"lat_x100000 must be in VN range [800_000, 2_400_000], got {self.lat_x100000}"
            )
        if not 10_200_000 <= self.lon_x100000 <= 11_000_000:
            raise ValueError(
                f"lon_x100000 must be in VN range [10_200_000, 11_000_000], got {self.lon_x100000}"
            )


@dataclass(frozen=True, slots=True)
class Reading:
    """One pollutant measurement from one station."""

    station_id: str
    pollutant: Pollutant
    value_x10: int  # concentration × 10
    observed_at: datetime
    quality: str = "GOOD"  # "GOOD", "CALIBRATING", "STALE"

    def __post_init__(self) -> None:
        if not self.station_id:
            raise ValueError("station_id must be non-empty")
        if self.value_x10 < 0:
            raise ValueError(f"value_x10 must be >= 0, got {self.value_x10}")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.quality not in ("GOOD", "CALIBRATING", "STALE"):
            raise ValueError(f"quality must be one of GOOD/CALIBRATING/STALE, got {self.quality!r}")


@dataclass(frozen=True, slots=True)
class WindowAverage:
    """Aggregate of ``Reading`` values over a fixed window per (station, pollutant)."""

    station_id: str
    pollutant: Pollutant
    window_start: datetime  # left-closed
    window_end: datetime  # right-open
    value_x10: int  # arithmetic mean × 10
    n_samples: int

    def __post_init__(self) -> None:
        if self.window_start >= self.window_end:
            raise ValueError(
                f"window_start {self.window_start} must be < window_end {self.window_end}"
            )
        if self.value_x10 < 0:
            raise ValueError(f"value_x10 must be >= 0, got {self.value_x10}")
        if self.n_samples < 1:
            raise ValueError(f"n_samples must be >= 1, got {self.n_samples}")


__all__ = [
    "VN_TZ",
    "Pollutant",
    "Reading",
    "Station",
    "StationKind",
    "WindowAverage",
]
