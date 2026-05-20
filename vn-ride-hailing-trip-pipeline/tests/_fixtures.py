"""Test fixtures: trip + fare builders."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vnride.schema import (
    VN_TZ,
    CancelledBy,
    FareBreakdown,
    PaymentMethod,
    ServiceType,
    Trip,
    TripState,
)

DEFAULT_TS = datetime(2026, 5, 18, 10, 0, 0, tzinfo=VN_TZ)


def make_fare(**overrides: Any) -> FareBreakdown:
    defaults: dict[str, Any] = {
        "base_vnd": 15_000,
        "distance_vnd": 60_000,
        "duration_vnd": 6_000,
        "booking_vnd": 3_000,
        "surge_multiplier_bps": 10_000,
    }
    defaults.update(overrides)
    return FareBreakdown(**defaults)


def make_completed(**overrides: Any) -> Trip:
    """Build a COMPLETED trip with sensible defaults."""
    defaults: dict[str, Any] = {
        "trip_id": "T-0001",
        "operator": "GRAB",
        "city": "SGN",
        "service": ServiceType.CAR,
        "rider_id": "R-0001",
        "driver_id": "D-0001",
        "state": TripState.COMPLETED,
        "requested_at": DEFAULT_TS,
        "completed_at": DEFAULT_TS,
        "distance_cm": 500_000,  # 5 km
        "duration_seconds": 900,  # 15 min
        "fare": make_fare(),
        "payment_method": PaymentMethod.EWALLET,
        "cancelled_by": None,
    }
    defaults.update(overrides)
    return Trip(**defaults)


def make_cancelled(**overrides: Any) -> Trip:
    defaults: dict[str, Any] = {
        "trip_id": "T-CXL",
        "operator": "GRAB",
        "city": "SGN",
        "service": ServiceType.BIKE,
        "rider_id": "R-0001",
        "driver_id": "D-0001",
        "state": TripState.CANCELLED,
        "requested_at": DEFAULT_TS,
        "completed_at": DEFAULT_TS,
        "cancelled_by": CancelledBy.RIDER,
    }
    defaults.update(overrides)
    return Trip(**defaults)


__all__ = ["DEFAULT_TS", "make_cancelled", "make_completed", "make_fare"]
