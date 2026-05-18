"""Canonical event builders for tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vntrip.schema import (
    VN_TZ,
    CancelBy,
    TripEvent,
    TripEventKind,
    VehicleClass,
)

DEFAULT_TS = datetime(2026, 5, 17, 9, 0, 0, tzinfo=VN_TZ)


def make_event(**overrides: Any) -> TripEvent:
    """Build a TripEvent with sane defaults — override any field."""
    defaults: dict[str, Any] = {
        "event_id": "E-0001",
        "trip_id": "T-0001",
        "rider_id": "R-0001",
        "driver_id": "",
        "kind": TripEventKind.REQUEST,
        "occurred_at": DEFAULT_TS,
        "district": "HCM:Q1",
        "lat_x10000": 1078000,
        "lon_x10000": 1067000,
        "vehicle_class": VehicleClass.MOTORBIKE,
        "distance_m": 0,
        "fare_vnd": 0,
        "surge_bps": 10_000,
        "cancel_by": None,
    }
    defaults.update(overrides)
    return TripEvent(**defaults)


def request_event(
    trip_id: str,
    rider: str,
    at: datetime,
    district: str = "HCM:Q1",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    surge: int = 10_000,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"REQ-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id="",
        kind=TripEventKind.REQUEST,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
        surge_bps=surge,
    )


def accept_event(
    trip_id: str,
    rider: str,
    driver: str,
    at: datetime,
    district: str = "HCM:Q1",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"ACC-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id=driver,
        kind=TripEventKind.ACCEPT,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
    )


def pickup_event(
    trip_id: str,
    rider: str,
    driver: str,
    at: datetime,
    district: str = "HCM:Q1",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"PKP-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id=driver,
        kind=TripEventKind.PICKUP,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
    )


def dropoff_event(
    trip_id: str,
    rider: str,
    driver: str,
    at: datetime,
    *,
    district: str = "HCM:Q3",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    distance_m: int = 5_000,
    fare_vnd: int = 30_000,
    surge_bps: int = 10_000,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"DRP-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id=driver,
        kind=TripEventKind.DROPOFF,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
        distance_m=distance_m,
        fare_vnd=fare_vnd,
        surge_bps=surge_bps,
    )


def cancel_event(
    trip_id: str,
    rider: str,
    driver: str,
    at: datetime,
    *,
    by: CancelBy,
    district: str = "HCM:Q1",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"CAN-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id=driver,
        kind=TripEventKind.CANCEL,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
        cancel_by=by,
    )


def expire_event(
    trip_id: str,
    rider: str,
    at: datetime,
    district: str = "HCM:Q1",
    vehicle: VehicleClass = VehicleClass.MOTORBIKE,
    event_id: str | None = None,
) -> TripEvent:
    return make_event(
        event_id=event_id or f"EXP-{trip_id}",
        trip_id=trip_id,
        rider_id=rider,
        driver_id="",
        kind=TripEventKind.EXPIRE,
        occurred_at=at,
        district=district,
        vehicle_class=vehicle,
    )


__all__ = [
    "DEFAULT_TS",
    "accept_event",
    "cancel_event",
    "dropoff_event",
    "expire_event",
    "make_event",
    "pickup_event",
    "request_event",
]
