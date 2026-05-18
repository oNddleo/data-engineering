"""VN AQI computation per **Quyết định 1459/QĐ-TCMT (2019)** + concentration
breakpoints from **QCVN 05:2023/BTNMT**.

The VN AQI methodology mirrors the US EPA's piecewise-linear interpolation
on per-pollutant breakpoints, but uses **VN-specific concentration cuts**
that reflect WHO 2021 guidance and local epidemiology:

    AQI(C) = (I_hi - I_lo) / (BP_hi - BP_lo) × (C - BP_lo) + I_lo

where ``C`` is the pollutant concentration in the appropriate
averaging window, and ``(BP_lo, BP_hi)`` is the breakpoint band that
contains ``C``. The composite station AQI is the **maximum** over the
six per-pollutant AQI values — the worst pollutant drives the
public-health message.

The AQI bands per QĐ 1459:

| Band                              | AQI range | Color   |
| --------------------------------- | --------- | ------- |
| Good (Tốt)                        | 0 – 50    | green   |
| Moderate (Trung bình)             | 51 – 100  | yellow  |
| Unhealthy for Sensitive Groups    | 101 – 150 | orange  |
| Unhealthy (Xấu)                   | 151 – 200 | red     |
| Very Unhealthy (Rất xấu)          | 201 – 300 | purple  |
| Hazardous (Nguy hại)              | 301 – 500 | maroon  |

Breakpoints below are from the QĐ 1459 + QCVN 05:2023 cross-reference.
All concentrations are in **µg/m³** except CO which is in **mg/m³**.
Internal storage is ``int(value × 10)`` matching ``schema.Reading``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aqipipe.schema import Pollutant


class AQIBand(str, Enum):
    """Six VN AQI bands per QĐ 1459."""

    GOOD = "GOOD"
    MODERATE = "MODERATE"
    UNHEALTHY_SENSITIVE = "UNHEALTHY_SENSITIVE"
    UNHEALTHY = "UNHEALTHY"
    VERY_UNHEALTHY = "VERY_UNHEALTHY"
    HAZARDOUS = "HAZARDOUS"


# AQI-index breakpoint table (I_lo, I_hi, band). Same across all
# pollutants; only the concentration breakpoints differ.
_AQI_BREAKS: tuple[tuple[int, int, AQIBand], ...] = (
    (0, 50, AQIBand.GOOD),
    (51, 100, AQIBand.MODERATE),
    (101, 150, AQIBand.UNHEALTHY_SENSITIVE),
    (151, 200, AQIBand.UNHEALTHY),
    (201, 300, AQIBand.VERY_UNHEALTHY),
    (301, 500, AQIBand.HAZARDOUS),
)


# Per-pollutant concentration breakpoints (in **µg/m³** × 10 for storage,
# except CO in **mg/m³** × 10). The tuple lengths match _AQI_BREAKS.
#
# Source: QĐ 1459/QĐ-TCMT 2019 Annex II, with QCVN 05:2023 reaffirming.
# PM2.5 / PM10 use 24-h averaging; NO2 / SO2 / O3 use 1-h; CO uses 8-h.
_POLLUTANT_BREAKS_X10: dict[Pollutant, tuple[tuple[int, int], ...]] = {
    Pollutant.PM25: (  # µg/m³ × 10 — 24-h average
        (0, 250),  # 0 – 25.0
        (251, 500),  # 25.1 – 50.0
        (501, 800),  # 50.1 – 80.0
        (801, 1500),  # 80.1 – 150.0
        (1501, 2500),  # 150.1 – 250.0
        (2501, 5000),  # 250.1 – 500.0
    ),
    Pollutant.PM10: (  # µg/m³ × 10 — 24-h average
        (0, 500),  # 0 – 50
        (501, 1500),  # 50.1 – 150
        (1501, 2500),  # 150.1 – 250
        (2501, 3500),  # 250.1 – 350
        (3501, 4200),  # 350.1 – 420
        (4201, 6000),  # 420.1 – 600
    ),
    Pollutant.NO2: (  # µg/m³ × 10 — 1-h
        (0, 1000),  # 0 – 100
        (1001, 2000),  # 100.1 – 200
        (2001, 7000),  # 200.1 – 700
        (7001, 12000),  # 700.1 – 1_200
        (12001, 23400),  # 1_200.1 – 2_340
        (23401, 31000),  # 2_340.1 – 3_100
    ),
    Pollutant.SO2: (  # µg/m³ × 10 — 1-h
        (0, 1250),  # 0 – 125
        (1251, 3500),  # 125.1 – 350
        (3501, 5500),  # 350.1 – 550
        (5501, 8000),  # 550.1 – 800
        (8001, 16000),  # 800.1 – 1_600
        (16001, 21000),  # 1_600.1 – 2_100
    ),
    Pollutant.O3: (  # µg/m³ × 10 — 1-h
        (0, 1600),  # 0 – 160
        (1601, 2000),  # 160.1 – 200
        (2001, 3000),  # 200.1 – 300
        (3001, 4000),  # 300.1 – 400
        (4001, 8000),  # 400.1 – 800
        (8001, 10000),  # 800.1 – 1_000
    ),
    Pollutant.CO: (  # mg/m³ × 10 — 8-h
        (0, 100),  # 0 – 10
        (101, 300),  # 10.1 – 30
        (301, 450),  # 30.1 – 45
        (451, 600),  # 45.1 – 60
        (601, 900),  # 60.1 – 90
        (901, 1200),  # 90.1 – 120
    ),
}


@dataclass(frozen=True, slots=True)
class PollutantAQI:
    """AQI contribution from one pollutant."""

    pollutant: Pollutant
    value_x10: int
    aqi: int
    band: AQIBand


def aqi_for(pollutant: Pollutant, value_x10: int) -> PollutantAQI:
    """Compute AQI for one pollutant concentration.

    Concentrations above the top breakpoint clamp to AQI 500 (HAZARDOUS).
    """
    if value_x10 < 0:
        raise ValueError(f"value_x10 must be >= 0, got {value_x10}")
    breaks = _POLLUTANT_BREAKS_X10[pollutant]
    for (bp_lo, bp_hi), (i_lo, i_hi, band) in zip(breaks, _AQI_BREAKS, strict=True):
        if bp_lo <= value_x10 <= bp_hi:
            # Piecewise-linear interpolation. Integer math throughout.
            if bp_hi == bp_lo:
                aqi = i_hi
            else:
                aqi = (i_hi - i_lo) * (value_x10 - bp_lo) // (bp_hi - bp_lo) + i_lo
            return PollutantAQI(pollutant=pollutant, value_x10=value_x10, aqi=aqi, band=band)
    # Above the top breakpoint — clamp to 500.
    return PollutantAQI(pollutant=pollutant, value_x10=value_x10, aqi=500, band=AQIBand.HAZARDOUS)


@dataclass(frozen=True, slots=True)
class StationAQI:
    """Composite AQI for one station — max over its pollutant readings."""

    station_id: str
    aqi: int
    dominant_pollutant: Pollutant
    band: AQIBand
    contributions: tuple[PollutantAQI, ...]


def station_aqi(station_id: str, readings_x10: dict[Pollutant, int]) -> StationAQI:
    """Compose station AQI = max over per-pollutant AQI values."""
    if not readings_x10:
        raise ValueError("readings_x10 must contain at least one pollutant")
    contributions = tuple(aqi_for(p, v) for p, v in readings_x10.items())
    worst = max(contributions, key=lambda c: c.aqi)
    return StationAQI(
        station_id=station_id,
        aqi=worst.aqi,
        dominant_pollutant=worst.pollutant,
        band=worst.band,
        contributions=contributions,
    )


def band_for_aqi(aqi: int) -> AQIBand:
    """Map a raw AQI integer to its band."""
    if aqi < 0:
        raise ValueError(f"aqi must be >= 0, got {aqi}")
    if aqi <= 50:
        return AQIBand.GOOD
    if aqi <= 100:
        return AQIBand.MODERATE
    if aqi <= 150:
        return AQIBand.UNHEALTHY_SENSITIVE
    if aqi <= 200:
        return AQIBand.UNHEALTHY
    if aqi <= 300:
        return AQIBand.VERY_UNHEALTHY
    return AQIBand.HAZARDOUS


__all__ = [
    "AQIBand",
    "PollutantAQI",
    "StationAQI",
    "aqi_for",
    "band_for_aqi",
    "station_aqi",
]
