"""Fare calculation — base + distance + duration + booking × surge.

The fare formula every VN ride-hailing operator advertises (2025):

.. code::

    fare = (base + distance_km · per_km + minutes · per_min) · surge
           + booking_fee

The **booking fee** is a flat platform charge that is *not* subject
to surge (it covers the in-app payment infrastructure). The remaining
three components scale linearly with surge.

We publish a default tariff matrix per ``ServiceType`` that matches
typical 2025 retail-grade pricing. Operators are free to override
with their own ``Tariff`` for testing.

Distances are in centimetres throughout the codebase (see schema)
to avoid float-km precision issues; we convert internally.

**Surge.** Bounded to [1.0×, 3.0×] — beyond 3× the regulator (Bộ
Công Thương) requires advance disclosure. Surge is encoded as basis
points (10_000 = 1.0×) for integer-VND arithmetic without float drift.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vnride.schema import FareBreakdown, ServiceType

MAX_SURGE_BPS = 30_000  # 3.0×, per regulator soft-cap
MIN_SURGE_BPS = 10_000  # 1.0× — no surge


@dataclass(frozen=True, slots=True)
class Tariff:
    """One service tier's fare schedule, all VND."""

    base_vnd: int  # flat starting fee
    per_km_vnd: int  # per km of distance
    per_minute_vnd: int  # per minute of duration
    booking_fee_vnd: int  # flat platform fee
    minimum_fare_vnd: int  # floor on the final amount


# Default VN retail tariff schedule (2025-ish blended).
DEFAULT_TARIFFS: dict[ServiceType, Tariff] = {
    ServiceType.CAR: Tariff(
        base_vnd=15_000,
        per_km_vnd=12_000,
        per_minute_vnd=400,
        booking_fee_vnd=3_000,
        minimum_fare_vnd=25_000,
    ),
    ServiceType.BIKE: Tariff(
        base_vnd=8_000,
        per_km_vnd=4_500,
        per_minute_vnd=200,
        booking_fee_vnd=2_000,
        minimum_fare_vnd=12_000,
    ),
    ServiceType.DELIVERY: Tariff(
        base_vnd=10_000,
        per_km_vnd=5_500,
        per_minute_vnd=300,
        booking_fee_vnd=2_500,
        minimum_fare_vnd=15_000,
    ),
}


def quote(
    service: ServiceType,
    distance_cm: int,
    duration_seconds: int,
    *,
    surge_bps: int = MIN_SURGE_BPS,
    tariff: Tariff | None = None,
) -> FareBreakdown:
    """Compute the fare breakdown for a completed trip.

    ``surge_bps`` defaults to no surge. Components are rounded to
    whole VND (the operator's in-app fare display rounds the same way).
    """
    if distance_cm < 0:
        raise ValueError(f"distance_cm must be >= 0, got {distance_cm}")
    if duration_seconds < 0:
        raise ValueError(f"duration_seconds must be >= 0, got {duration_seconds}")
    if not MIN_SURGE_BPS <= surge_bps <= MAX_SURGE_BPS:
        raise ValueError(
            f"surge_bps must be in [{MIN_SURGE_BPS}, {MAX_SURGE_BPS}], " f"got {surge_bps}",
        )

    t = tariff if tariff is not None else DEFAULT_TARIFFS[service]
    km = distance_cm / 100_000
    minutes = duration_seconds / 60

    # Surge-multiplied components (use ceil-style integer math).
    base_surged = (t.base_vnd * surge_bps + 9_999) // 10_000
    distance_unsurged = math.ceil(km * t.per_km_vnd)
    distance_surged = (distance_unsurged * surge_bps + 9_999) // 10_000
    duration_unsurged = math.ceil(minutes * t.per_minute_vnd)
    duration_surged = (duration_unsurged * surge_bps + 9_999) // 10_000

    # Booking fee is NOT subject to surge.
    booking = t.booking_fee_vnd

    breakdown = FareBreakdown(
        base_vnd=base_surged,
        distance_vnd=distance_surged,
        duration_vnd=duration_surged,
        booking_vnd=booking,
        surge_multiplier_bps=surge_bps,
    )
    # Enforce minimum-fare floor — bump the base.
    deficit = t.minimum_fare_vnd - breakdown.total_vnd
    if deficit > 0:
        breakdown = FareBreakdown(
            base_vnd=base_surged + deficit,
            distance_vnd=distance_surged,
            duration_vnd=duration_surged,
            booking_vnd=booking,
            surge_multiplier_bps=surge_bps,
        )
    return breakdown


def commission_split(
    fare: FareBreakdown,
    commission_bps_val: int,
) -> tuple[int, int]:
    """Split a fare into (operator commission, driver payout) in VND.

    Operator commission is taken on the **fare excluding the booking
    fee** — booking fees flow entirely to the operator. Returns
    ``(operator_take, driver_net)`` where both sum to fare.total_vnd.
    """
    if not 0 <= commission_bps_val <= 10_000:
        raise ValueError(
            f"commission_bps must be in [0, 10_000], got {commission_bps_val}",
        )
    ride_revenue = fare.total_vnd - fare.booking_vnd
    operator_cut = (ride_revenue * commission_bps_val + 9_999) // 10_000
    driver_net = ride_revenue - operator_cut
    operator_total = operator_cut + fare.booking_vnd
    return operator_total, driver_net


__all__ = [
    "DEFAULT_TARIFFS",
    "MAX_SURGE_BPS",
    "MIN_SURGE_BPS",
    "Tariff",
    "commission_split",
    "quote",
]
