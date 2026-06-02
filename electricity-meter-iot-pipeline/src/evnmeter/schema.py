"""Smart-meter schema modelled on EVN's CT-2014 / ECM-7510 telemetry.

EVN (Electricity of Vietnam — the state-owned monopoly utility) has
been rolling out smart meters across the country since 2018. The
meters emit **cumulative kWh** readings every 30 minutes; consumption
is *derived* by the back-office (this pipeline) rather than transmitted
directly.

Key invariants the schema enforces:

* ``cumulative_kwh_x100`` is stored as ``int(kWh × 100)`` — two
  decimal places of precision. Float drift is unacceptable for a
  legally-billable measurement.
* Meter readings are monotonically non-decreasing **per meter**, except
  on **rollover** (cumulative wraps from ``9_999_999`` back to ``0``).
* All timestamps are timezone-aware. EVN meters report in ``VN_TZ``
  (UTC+7) but the pipeline tolerates UTC or any tz-aware input.

The ``MeterKind`` enum distinguishes single-phase residential
(``RESI_1P``), three-phase residential (``RESI_3P``), and commercial
(``COMM``). Different kinds have different tariff structures —
residential uses a 6-tier progressive table, commercial uses TOU
(time-of-use) pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


# Meter rollover threshold — cumulative reading wraps to 0 after this.
# EVN's standard residential meter has 7 integer digits.
METER_MAX_X100 = 999_999_999  # 9_999_999.99 kWh × 100


class MeterKind(str, Enum):
    """The three meter classes EVN bills against."""

    RESI_1P = "RESI_1P"  # Single-phase residential (most homes)
    RESI_3P = "RESI_3P"  # Three-phase residential (large villas)
    COMM = "COMM"  # Commercial / industrial — uses TOU tariff


@dataclass(frozen=True, slots=True)
class Meter:
    """Static meter metadata."""

    meter_id: str  # EVN serial number
    customer_id: str
    kind: MeterKind
    region_code: str  # "HCMC", "HN", "DN", "CT", "HP", "NT", "BD", "BTH"
    installed_at: datetime

    def __post_init__(self) -> None:
        if not self.meter_id:
            raise ValueError("meter_id must be non-empty")
        if not self.customer_id:
            raise ValueError("customer_id must be non-empty")
        if not self.region_code:
            raise ValueError("region_code must be non-empty")
        if self.installed_at.tzinfo is None:
            raise ValueError("installed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Reading:
    """One cumulative-kWh reading from a smart meter."""

    meter_id: str
    cumulative_kwh_x100: int  # kWh × 100 — integer to avoid float drift
    observed_at: datetime
    quality: str = "GOOD"  # "GOOD", "ESTIMATED", "PARTIAL"

    def __post_init__(self) -> None:
        if not self.meter_id:
            raise ValueError("meter_id must be non-empty")
        if not 0 <= self.cumulative_kwh_x100 <= METER_MAX_X100:
            raise ValueError(
                f"cumulative_kwh_x100 must be in [0, {METER_MAX_X100}], "
                f"got {self.cumulative_kwh_x100}"
            )
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.quality not in ("GOOD", "ESTIMATED", "PARTIAL"):
            raise ValueError(
                f"quality must be one of GOOD / ESTIMATED / PARTIAL, got {self.quality!r}"
            )


@dataclass(frozen=True, slots=True)
class ConsumptionInterval:
    """Derived interval consumption — output of the cumulative→delta pass."""

    meter_id: str
    start_at: datetime  # left-closed
    end_at: datetime  # right-open
    kwh_x100: int  # delta over the interval
    is_estimated: bool  # True when a gap was filled by interpolation

    def __post_init__(self) -> None:
        if self.start_at >= self.end_at:
            raise ValueError(f"start_at {self.start_at} must be < end_at {self.end_at}")
        if self.kwh_x100 < 0:
            raise ValueError(f"kwh_x100 must be >= 0, got {self.kwh_x100}")
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at + end_at must be timezone-aware")


__all__ = [
    "METER_MAX_X100",
    "VN_TZ",
    "ConsumptionInterval",
    "Meter",
    "MeterKind",
    "Reading",
]
