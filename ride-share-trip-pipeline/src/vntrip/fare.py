"""Fare calculator — matches the published GrabBike / GrabCar / GojekCar
VN pricing structure.

The fare has four components:

1. **Base fare** — flat amount paid at trip start. Varies by
   vehicle class.
2. **Distance fare** — VND per kilometre over the ``free_km`` portion.
3. **Time fare** — VND per minute of ride. Small adjustment for
   the in-vehicle time.
4. **Surge multiplier** — applied to the pre-surge subtotal during
   peak-demand windows. ``10_000 bps = 1.0×``, ``15_000 bps = 1.5×``.

All computation in integer VND with banker's rounding (`round()` in
Python 3) — matches the rest of the catalogue (e.g.
``healthcare-claims-processor``).

Published rates (per Grab VN consumer-app help, May 2026):

| Vehicle    | Base (VND) | First km included | VND/km | VND/min |
| ---------- | ---------- | ----------------- | ------ | ------- |
| MOTORBIKE  | 12,000     | 2 km              | 4,000  | 200     |
| CAR_4      | 25,000     | 2 km              | 11,000 | 400     |
| CAR_7      | 30,000     | 2 km              | 13,000 | 500     |
| DELIVERY   | 15,000     | 2 km              | 5,000  | 0       |

These are configurable via the ``rate_card`` keyword.
"""

from __future__ import annotations

from dataclasses import dataclass

from vntrip.schema import FareBreakdown, VehicleClass


@dataclass(frozen=True, slots=True)
class FareRate:
    """One row of the rate card for a vehicle class."""

    base_fare_vnd: int
    free_km: int  # km included in the base
    per_km_vnd: int  # VND per km after free_km
    per_minute_vnd: int  # VND per minute of ride time


# Default published Grab VN rates (May 2026).
DEFAULT_RATE_CARD: dict[VehicleClass, FareRate] = {
    VehicleClass.MOTORBIKE: FareRate(
        base_fare_vnd=12_000, free_km=2, per_km_vnd=4_000, per_minute_vnd=200
    ),
    VehicleClass.CAR_4: FareRate(
        base_fare_vnd=25_000, free_km=2, per_km_vnd=11_000, per_minute_vnd=400
    ),
    VehicleClass.CAR_7: FareRate(
        base_fare_vnd=30_000, free_km=2, per_km_vnd=13_000, per_minute_vnd=500
    ),
    VehicleClass.DELIVERY: FareRate(
        base_fare_vnd=15_000, free_km=2, per_km_vnd=5_000, per_minute_vnd=0
    ),
}


def compute_fare(
    *,
    trip_id: str,
    vehicle_class: VehicleClass,
    distance_m: int,
    ride_seconds: int,
    surge_bps: int = 10_000,
    rate_card: dict[VehicleClass, FareRate] | None = None,
) -> FareBreakdown:
    """Compute the full fare breakdown for a completed trip.

    All inputs must be non-negative integers; ``surge_bps`` must be
    ``>= 10000`` (no negative surge).
    """
    if distance_m < 0:
        raise ValueError(f"distance_m must be >= 0, got {distance_m}")
    if ride_seconds < 0:
        raise ValueError(f"ride_seconds must be >= 0, got {ride_seconds}")
    if surge_bps < 10_000:
        raise ValueError(f"surge_bps must be >= 10000, got {surge_bps}")

    card = rate_card if rate_card is not None else DEFAULT_RATE_CARD
    if vehicle_class not in card:
        raise ValueError(f"unknown vehicle_class: {vehicle_class}")
    rate = card[vehicle_class]

    chargeable_m = max(0, distance_m - rate.free_km * 1_000)
    # Distance fare: round( chargeable_m / 1000 * per_km_vnd ) via integer math.
    # Bankers'-rounded division: (n + d/2) // d, BUT real banker's is round-half-to-even.
    distance_fare = _banker_div(chargeable_m * rate.per_km_vnd, 1_000)

    ride_minutes_x1000 = ride_seconds * 1_000 // 60  # integer minutes × 1000
    time_fare = _banker_div(ride_minutes_x1000 * rate.per_minute_vnd, 1_000)

    pre_surge = rate.base_fare_vnd + distance_fare + time_fare
    # Total fare = pre_surge × surge_bps / 10_000, banker-rounded.
    total = _banker_div(pre_surge * surge_bps, 10_000)

    return FareBreakdown(
        trip_id=trip_id,
        base_fare_vnd=rate.base_fare_vnd,
        distance_fare_vnd=distance_fare,
        time_fare_vnd=time_fare,
        surge_multiplier_bps=surge_bps,
        pre_surge_subtotal_vnd=pre_surge,
        total_fare_vnd=total,
    )


def _banker_div(numerator: int, denominator: int) -> int:
    """Integer division with banker's (round-half-to-even) rounding."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    q, r = divmod(numerator, denominator)
    # Compare 2r vs denominator for half-rounding.
    twice = 2 * r
    if twice < denominator:
        return q
    if twice > denominator:
        return q + 1
    # Exactly half — pick even.
    return q if q % 2 == 0 else q + 1


__all__ = ["DEFAULT_RATE_CARD", "FareRate", "compute_fare"]
