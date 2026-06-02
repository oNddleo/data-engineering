"""Seeded synthetic trip stream generator.

Generates a month of realistic VN ride-hailing activity:

* Riders + drivers allocated by operator market share and city
  population.
* Per-day mix per rider: 0-3 trips (commute pattern).
* Service mix: 55% BIKE, 35% CAR, 10% DELIVERY (per Grab 2024 figures).
* 5% of requests fail with NO_DRIVER; another 8% are CANCELLED by
  rider or driver.
* Peak hours (07:00-09:00 and 17:00-19:00 local) apply city-default
  surge multiplier; off-peak is 1.0×.
* Configurable fraud-positive cohorts:
  - ``ghost_fraction``      — riders who collude on micro-trips
  - ``cancel_abuse_fraction`` — drivers who cancel > 50% of their work
  - ``surge_gaming_fraction`` — (rider, driver) pairs only ever paired
    during surge windows
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from vnride.operators import all_cities, all_operators
from vnride.pricing import MIN_SURGE_BPS, quote
from vnride.schema import (
    VN_TZ,
    CancelledBy,
    PaymentMethod,
    ServiceType,
    Trip,
    TripState,
)


def generate(
    *,
    n_riders: int = 50,
    n_drivers: int = 20,
    n_days: int = 30,
    base_time: datetime | None = None,
    no_driver_rate: float = 0.05,
    cancel_rate: float = 0.08,
    ghost_fraction: float = 0.02,
    cancel_abuse_fraction: float = 0.05,
    surge_gaming_fraction: float = 0.02,
    seed: int = 0,
) -> list[Trip]:
    """Generate a synthetic month of ride-hailing activity."""
    if n_riders < 0 or n_drivers < 0:
        raise ValueError("n_riders / n_drivers must be >= 0")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    for name, frac in (
        ("no_driver_rate", no_driver_rate),
        ("cancel_rate", cancel_rate),
        ("ghost_fraction", ghost_fraction),
        ("cancel_abuse_fraction", cancel_abuse_fraction),
        ("surge_gaming_fraction", surge_gaming_fraction),
    ):
        if not 0 <= frac <= 1:
            raise ValueError(f"{name} must be in [0, 1], got {frac}")

    rng = random.Random(seed)
    base = base_time or datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
    operators = all_operators()
    op_weights = [o.market_share_pct for o in operators]
    cities = all_cities()
    city_weights = [c.population_thousands for c in cities]

    rider_ids = [f"R-{i:07d}" for i in range(n_riders)]
    driver_ids = [f"D-{i:07d}" for i in range(n_drivers)]

    # Fraud-positive cohorts (disjoint among drivers, plus a rider cohort).
    drivers_pool = list(driver_ids)
    rng.shuffle(drivers_pool)
    n_cancel_abuse = max(0, int(n_drivers * cancel_abuse_fraction))
    cancel_abuse_drivers = set(drivers_pool[:n_cancel_abuse])

    riders_pool = list(rider_ids)
    rng.shuffle(riders_pool)
    n_ghost = max(0, int(n_riders * ghost_fraction))
    ghost_riders = set(riders_pool[:n_ghost])

    # Pair (rider, driver) for surge-gaming.
    n_surge_pairs = max(0, int(min(n_riders, n_drivers) * surge_gaming_fraction))
    surge_pairs: set[tuple[str, str]] = set()
    for i in range(n_surge_pairs):
        surge_pairs.add((rider_ids[i], driver_ids[i % n_drivers]))

    trips: list[Trip] = []
    counter = 0

    def _tid() -> str:
        nonlocal counter
        tid = f"T-{counter:012d}"
        counter += 1
        return tid

    def _is_peak(hour: int) -> bool:
        return 7 <= hour < 9 or 17 <= hour < 19

    for day in range(n_days):
        day_start = base + timedelta(days=day)
        for rider_id in rider_ids:
            for _ in range(rng.randint(0, 3)):
                hour = rng.randint(6, 22)
                operator = rng.choices(operators, weights=op_weights, k=1)[0]
                city = rng.choices(cities, weights=city_weights, k=1)[0]
                service = rng.choices(
                    [ServiceType.BIKE, ServiceType.CAR, ServiceType.DELIVERY],
                    weights=[55, 35, 10],
                    k=1,
                )[0]
                requested_at = day_start + timedelta(
                    hours=hour,
                    minutes=rng.randint(0, 59),
                )

                # Outcome dispatch.
                roll = rng.random()
                if roll < no_driver_rate:
                    trips.append(
                        Trip(
                            trip_id=_tid(),
                            operator=operator.abbreviation,
                            city=city.code,
                            service=service,
                            rider_id=rider_id,
                            driver_id="",
                            state=TripState.NO_DRIVER,
                            requested_at=requested_at,
                            completed_at=requested_at + timedelta(minutes=3),
                            cancelled_by=CancelledBy.SYSTEM,
                        )
                    )
                    continue

                # Choose a driver — surge-gamed pair takes priority.
                driver_id: str
                gamed_driver: str | None = None
                for pair in surge_pairs:
                    if pair[0] == rider_id:
                        gamed_driver = pair[1]
                        break
                if gamed_driver is not None and _is_peak(hour):
                    driver_id = gamed_driver
                else:
                    driver_id = rng.choice(driver_ids)

                # Cancel branch: rider/driver cancels before pickup.
                normal_cancel = rng.random() < cancel_rate
                abuse_cancel = driver_id in cancel_abuse_drivers and rng.random() < 0.85
                if normal_cancel or abuse_cancel:
                    trips.append(
                        Trip(
                            trip_id=_tid(),
                            operator=operator.abbreviation,
                            city=city.code,
                            service=service,
                            rider_id=rider_id,
                            driver_id=driver_id,
                            state=TripState.CANCELLED,
                            requested_at=requested_at,
                            completed_at=requested_at + timedelta(minutes=rng.randint(1, 8)),
                            cancelled_by=rng.choice([CancelledBy.RIDER, CancelledBy.DRIVER]),
                        )
                    )
                    continue

                # Happy path: COMPLETED. Distance + duration.
                if rider_id in ghost_riders and rng.random() < 0.5:
                    # Ghost ride — tiny distance + duration.
                    distance_cm = rng.randint(500, 5_000)  # 5-50 m
                    duration = rng.randint(5, 25)
                else:
                    # Normal trip; distance depends on service.
                    if service is ServiceType.BIKE:
                        km = rng.uniform(0.8, 8.0)
                    elif service is ServiceType.CAR:
                        km = rng.uniform(2.0, 25.0)
                    else:  # DELIVERY
                        km = rng.uniform(1.0, 12.0)
                    distance_cm = int(km * 100_000)
                    speed_kmh = rng.uniform(15, 35)
                    duration = int((km / speed_kmh) * 3600)

                pair_is_gamed = (rider_id, driver_id) in surge_pairs
                if _is_peak(hour) and (pair_is_gamed or rng.random() < 0.3):
                    surge_bps = city.base_surge_during_peak_bps
                else:
                    surge_bps = MIN_SURGE_BPS

                fare = quote(service, distance_cm, duration, surge_bps=surge_bps)
                payment = rng.choices(
                    [PaymentMethod.CASH, PaymentMethod.EWALLET, PaymentMethod.BANK_CARD],
                    weights=[45, 40, 15],
                    k=1,
                )[0]
                trips.append(
                    Trip(
                        trip_id=_tid(),
                        operator=operator.abbreviation,
                        city=city.code,
                        service=service,
                        rider_id=rider_id,
                        driver_id=driver_id,
                        state=TripState.COMPLETED,
                        requested_at=requested_at,
                        completed_at=requested_at + timedelta(seconds=duration + 180),
                        distance_cm=distance_cm,
                        duration_seconds=duration,
                        fare=fare,
                        payment_method=payment,
                    )
                )

    trips.sort(key=lambda t: (t.requested_at, t.trip_id))
    return trips


__all__ = ["generate"]
