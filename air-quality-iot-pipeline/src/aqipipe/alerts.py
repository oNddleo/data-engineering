"""Health-warning alerts from station AQIs.

The VN Ministry of Health publishes guidance per AQI band:

| Band                              | Public message                                |
| --------------------------------- | --------------------------------------------- |
| GOOD                              | (no alert)                                    |
| MODERATE                          | (no alert)                                    |
| UNHEALTHY_SENSITIVE               | sensitive groups should limit outdoor time    |
| UNHEALTHY                         | everyone should limit outdoor time            |
| VERY_UNHEALTHY                    | avoid outdoor activity; close windows         |
| HAZARDOUS                         | stay indoors; air purifiers; N95 if outside   |

The alert system emits one ``Alert`` per ``(station_id, band ≥ threshold)``
crossing. Callers pin the threshold band (default UNHEALTHY_SENSITIVE)
— anything below is silently suppressed.

Sensitive-group escalation: separate ``find_sensitive_alerts`` emits
warnings starting at MODERATE for children / elderly / asthma cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from aqipipe.qcvn import AQIBand

if TYPE_CHECKING:
    from datetime import datetime

    from aqipipe.qcvn import StationAQI


_BAND_RANK: dict[AQIBand, int] = {
    AQIBand.GOOD: 0,
    AQIBand.MODERATE: 1,
    AQIBand.UNHEALTHY_SENSITIVE: 2,
    AQIBand.UNHEALTHY: 3,
    AQIBand.VERY_UNHEALTHY: 4,
    AQIBand.HAZARDOUS: 5,
}


class AlertKind(str, Enum):
    """Two alert channels."""

    PUBLIC = "PUBLIC"  # general public warning
    SENSITIVE = "SENSITIVE"  # children / elderly / asthma / respiratory cohort


@dataclass(frozen=True, slots=True)
class Alert:
    """One actionable health-warning event."""

    kind: AlertKind
    station_id: str
    aqi: int
    band: AQIBand
    detected_at: datetime
    detail: str


def _band_message(band: AQIBand) -> str:
    """Stock VN-MoH public message per band."""
    return {
        AQIBand.GOOD: "no alert",
        AQIBand.MODERATE: "no alert",
        AQIBand.UNHEALTHY_SENSITIVE: "sensitive groups should limit outdoor time",
        AQIBand.UNHEALTHY: "everyone should limit outdoor time",
        AQIBand.VERY_UNHEALTHY: "avoid outdoor activity; close windows",
        AQIBand.HAZARDOUS: "stay indoors; air purifiers on; N95 if outside",
    }[band]


def find_public_alerts(
    aqis: dict[str, StationAQI],
    now: datetime,
    *,
    min_band: AQIBand = AQIBand.UNHEALTHY_SENSITIVE,
) -> list[Alert]:
    """Emit one ``Alert`` per station ≥ ``min_band``.

    Sorted by ``(aqi desc, station_id)`` so dashboards highlight the
    worst air first.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    threshold = _BAND_RANK[min_band]
    out: list[Alert] = []
    for sid, sa in aqis.items():
        if _BAND_RANK[sa.band] < threshold:
            continue
        out.append(
            Alert(
                kind=AlertKind.PUBLIC,
                station_id=sid,
                aqi=sa.aqi,
                band=sa.band,
                detected_at=now,
                detail=(
                    f"AQI {sa.aqi} ({sa.band.value}) — {_band_message(sa.band)} "
                    f"[dominant: {sa.dominant_pollutant.value}]"
                ),
            )
        )
    out.sort(key=lambda a: (-a.aqi, a.station_id))
    return out


def find_sensitive_alerts(
    aqis: dict[str, StationAQI],
    now: datetime,
) -> list[Alert]:
    """Sensitive-group alerts fire one band earlier (starting at MODERATE).

    The methodology: children, elderly, and respiratory-condition
    cohorts react adversely at concentrations the general public
    tolerates. VN-MoH guidance escalates these one band early.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    threshold = _BAND_RANK[AQIBand.MODERATE]
    out: list[Alert] = []
    for sid, sa in aqis.items():
        if _BAND_RANK[sa.band] < threshold:
            continue
        out.append(
            Alert(
                kind=AlertKind.SENSITIVE,
                station_id=sid,
                aqi=sa.aqi,
                band=sa.band,
                detected_at=now,
                detail=(
                    f"AQI {sa.aqi} ({sa.band.value}) — sensitive groups: "
                    f"limit outdoor exposure [dominant: {sa.dominant_pollutant.value}]"
                ),
            )
        )
    out.sort(key=lambda a: (-a.aqi, a.station_id))
    return out


def band_distribution(
    aqis: dict[str, StationAQI],
) -> dict[AQIBand, int]:
    """Count of stations per band — for ops dashboards."""
    counts: dict[AQIBand, int] = {b: 0 for b in AQIBand}
    for sa in aqis.values():
        counts[sa.band] += 1
    return counts


__all__ = [
    "Alert",
    "AlertKind",
    "band_distribution",
    "find_public_alerts",
    "find_sensitive_alerts",
]
