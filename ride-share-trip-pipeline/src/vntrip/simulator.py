"""Seeded synthetic trip-event stream.

Five trip outcomes per simulated REQUEST:

| Outcome                | Default mix |
| ---------------------- | ----------- |
| completed normally     | 70%         |
| expired (no driver)    | 5%          |
| cancelled by rider     | 8%          |
| cancelled by driver    | 12%         |
| **cancel-abuse**       | 3%          |
| **phantom completion** | 2%          |

A small fraction of drivers are configured as "abusive" — they
accept-and-cancel within seconds. A small fraction of completed
trips have implausibly short distance/duration (phantom).

Surge multipliers spike during 07:00-09:00 + 17:00-19:00 (VN rush
hours).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from vntrip.districts import all_codes
from vntrip.fare import compute_fare
from vntrip.schema import (
    VN_TZ,
    CancelBy,
    TripEvent,
    TripEventKind,
    VehicleClass,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 6, 0, 0, tzinfo=VN_TZ)

_VEHICLE_MIX: tuple[tuple[VehicleClass, float], ...] = (
    (VehicleClass.MOTORBIKE, 0.65),
    (VehicleClass.CAR_4, 0.20),
    (VehicleClass.CAR_7, 0.05),
    (VehicleClass.DELIVERY, 0.10),
)


def _pick_vehicle(rng: random.Random) -> VehicleClass:
    r = rng.random()
    cumulative = 0.0
    for cls, w in _VEHICLE_MIX:
        cumulative += w
        if r < cumulative:
            return cls
    return VehicleClass.MOTORBIKE


def _is_rush_hour(ts: datetime) -> bool:
    h = ts.astimezone(VN_TZ).hour
    return (7 <= h < 9) or (17 <= h < 19)


def _surge_for(ts: datetime, rng: random.Random) -> int:
    """Surge multiplier in bps. 10_000 = 1.0×."""
    if _is_rush_hour(ts):
        return rng.choice((12_000, 13_000, 15_000, 18_000, 20_000))
    return rng.choice((10_000, 10_000, 10_000, 11_000))


def generate(
    *,
    n_riders: int = 100,
    n_drivers: int = 30,
    n_days: int = 7,
    trips_per_rider_per_day: float = 1.5,
    expire_fraction: float = 0.05,
    rider_cancel_fraction: float = 0.08,
    driver_cancel_fraction: float = 0.12,
    cancel_abuse_fraction: float = 0.03,
    phantom_fraction: float = 0.02,
    seed: int = 0,
    base_time: datetime | None = None,
) -> list[TripEvent]:
    """Generate a mixed trip-event stream over ``n_days`` days."""
    fractions = (
        expire_fraction,
        rider_cancel_fraction,
        driver_cancel_fraction,
        cancel_abuse_fraction,
        phantom_fraction,
    )
    if any(not 0 <= f <= 1 for f in fractions):
        raise ValueError("each fraction must be in [0, 1]")
    if sum(fractions) > 1.0 + 1e-9:
        raise ValueError(f"non-completed fractions sum to {sum(fractions)} > 1.0")
    if n_riders < 1 or n_drivers < 1 or n_days < 1:
        raise ValueError("n_riders / n_drivers / n_days must be >= 1")
    if trips_per_rider_per_day < 0:
        raise ValueError("trips_per_rider_per_day must be >= 0")

    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    districts = all_codes()

    events: list[TripEvent] = []
    counters = {"event": 0, "trip": 0}

    def next_event_id() -> str:
        eid = f"E-{counters['event']:08d}"
        counters["event"] += 1
        return eid

    def next_trip_id() -> str:
        tid = f"T-{counters['trip']:08d}"
        counters["trip"] += 1
        return tid

    riders = [f"R-{i:05d}" for i in range(n_riders)]
    drivers = [f"D-{i:05d}" for i in range(n_drivers)]
    # 10% of drivers are "abusive" — they get a disproportionate share
    # of cancel-abuse trips.
    n_abusive = max(1, n_drivers // 10)
    abusive_drivers = drivers[:n_abusive]

    cum = (
        expire_fraction,
        expire_fraction + rider_cancel_fraction,
        expire_fraction + rider_cancel_fraction + driver_cancel_fraction,
        expire_fraction + rider_cancel_fraction + driver_cancel_fraction + cancel_abuse_fraction,
        expire_fraction
        + rider_cancel_fraction
        + driver_cancel_fraction
        + cancel_abuse_fraction
        + phantom_fraction,
    )
    for day in range(n_days):
        for rider in riders:
            for _ in range(int(rng.gauss(trips_per_rider_per_day, 0.5)) + 1):
                if rng.random() > 0.85:
                    continue
                hour = rng.randint(6, 22)
                minute = rng.randint(0, 59)
                req_at = (base + timedelta(days=day)).replace(
                    hour=hour,
                    minute=minute,
                    second=rng.randint(0, 59),
                )
                trip_id = next_trip_id()
                vehicle = _pick_vehicle(rng)
                origin = rng.choice(districts)
                dest = rng.choice(districts)
                surge = _surge_for(req_at, rng)
                events.append(
                    TripEvent(
                        event_id=next_event_id(),
                        trip_id=trip_id,
                        rider_id=rider,
                        driver_id="",
                        kind=TripEventKind.REQUEST,
                        occurred_at=req_at,
                        district=origin,
                        vehicle_class=vehicle,
                        surge_bps=surge,
                    )
                )
                r = rng.random()
                if r < cum[0]:
                    _emit_expire(events, next_event_id, trip_id, rider, req_at, origin, vehicle)
                elif r < cum[1]:
                    _emit_rider_cancel(
                        events, next_event_id, trip_id, rider, req_at, origin, vehicle, rng
                    )
                elif r < cum[2]:
                    driver = rng.choice(drivers)
                    _emit_driver_cancel(
                        events,
                        next_event_id,
                        trip_id,
                        rider,
                        driver,
                        req_at,
                        origin,
                        vehicle,
                        rng,
                        fast=False,
                    )
                elif r < cum[3]:
                    driver = rng.choice(abusive_drivers)
                    _emit_driver_cancel(
                        events,
                        next_event_id,
                        trip_id,
                        rider,
                        driver,
                        req_at,
                        origin,
                        vehicle,
                        rng,
                        fast=True,
                    )
                elif r < cum[4]:
                    driver = rng.choice(drivers)
                    _emit_complete(
                        events,
                        next_event_id,
                        trip_id,
                        rider,
                        driver,
                        req_at,
                        origin,
                        dest,
                        vehicle,
                        surge,
                        rng,
                        phantom=True,
                    )
                else:
                    driver = rng.choice(drivers)
                    _emit_complete(
                        events,
                        next_event_id,
                        trip_id,
                        rider,
                        driver,
                        req_at,
                        origin,
                        dest,
                        vehicle,
                        surge,
                        rng,
                        phantom=False,
                    )
    events.sort(key=lambda e: (e.occurred_at, e.event_id))
    return events


def _emit_expire(
    events: list[TripEvent],
    next_id: Callable[[], str],
    trip_id: str,
    rider: str,
    req_at: datetime,
    district: str,
    vehicle: VehicleClass,
) -> None:
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id="",
            kind=TripEventKind.EXPIRE,
            occurred_at=req_at + timedelta(minutes=5),
            district=district,
            vehicle_class=vehicle,
        )
    )


def _emit_rider_cancel(
    events: list[TripEvent],
    next_id: Callable[[], str],
    trip_id: str,
    rider: str,
    req_at: datetime,
    district: str,
    vehicle: VehicleClass,
    rng: random.Random,
) -> None:
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id="",
            kind=TripEventKind.CANCEL,
            occurred_at=req_at + timedelta(seconds=rng.randint(10, 90)),
            district=district,
            vehicle_class=vehicle,
            cancel_by=CancelBy.RIDER,
        )
    )


def _emit_driver_cancel(
    events: list[TripEvent],
    next_id: Callable[[], str],
    trip_id: str,
    rider: str,
    driver: str,
    req_at: datetime,
    district: str,
    vehicle: VehicleClass,
    rng: random.Random,
    *,
    fast: bool,
) -> None:
    accept_at = req_at + timedelta(seconds=rng.randint(15, 60))
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id=driver,
            kind=TripEventKind.ACCEPT,
            occurred_at=accept_at,
            district=district,
            vehicle_class=vehicle,
        )
    )
    delta = rng.randint(2, 15) if fast else rng.randint(60, 240)
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id=driver,
            kind=TripEventKind.CANCEL,
            occurred_at=accept_at + timedelta(seconds=delta),
            district=district,
            vehicle_class=vehicle,
            cancel_by=CancelBy.DRIVER,
        )
    )


def _emit_complete(
    events: list[TripEvent],
    next_id: Callable[[], str],
    trip_id: str,
    rider: str,
    driver: str,
    req_at: datetime,
    origin: str,
    dest: str,
    vehicle: VehicleClass,
    surge: int,
    rng: random.Random,
    *,
    phantom: bool,
) -> None:
    accept_at = req_at + timedelta(seconds=rng.randint(20, 120))
    pickup_at = accept_at + timedelta(seconds=rng.randint(60, 600))
    if phantom:
        distance_m = rng.randint(20, 180)
        ride_seconds = rng.randint(5, 28)
    else:
        distance_m = rng.randint(1_500, 18_000)
        ride_seconds = rng.randint(360, 1_800)
    dropoff_at = pickup_at + timedelta(seconds=ride_seconds)
    fare = compute_fare(
        trip_id=trip_id,
        vehicle_class=vehicle,
        distance_m=distance_m,
        ride_seconds=ride_seconds,
        surge_bps=surge,
    )
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id=driver,
            kind=TripEventKind.ACCEPT,
            occurred_at=accept_at,
            district=origin,
            vehicle_class=vehicle,
        )
    )
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id=driver,
            kind=TripEventKind.PICKUP,
            occurred_at=pickup_at,
            district=origin,
            vehicle_class=vehicle,
        )
    )
    events.append(
        TripEvent(
            event_id=next_id(),
            trip_id=trip_id,
            rider_id=rider,
            driver_id=driver,
            kind=TripEventKind.DROPOFF,
            occurred_at=dropoff_at,
            district=dest,
            vehicle_class=vehicle,
            distance_m=distance_m,
            fare_vnd=fare.total_fare_vnd,
            surge_bps=surge,
        )
    )


__all__ = ["generate"]
