"""Pricing: tariff lookup, surge, minimum fare, commission split."""

from __future__ import annotations

import pytest

from vnride.pricing import (
    DEFAULT_TARIFFS,
    MAX_SURGE_BPS,
    MIN_SURGE_BPS,
    commission_split,
    quote,
)
from vnride.schema import ServiceType

from ._fixtures import make_fare

# ---------- quote -----------------------------------------------------------


def test_quote_car_basic() -> None:
    """A 5 km / 15 min CAR trip, no surge."""
    fare = quote(
        ServiceType.CAR,
        distance_cm=500_000,  # 5 km
        duration_seconds=900,  # 15 min
    )
    # base 15_000 + 60_000 (5 km × 12_000) + 6_000 (15 min × 400) + 3_000 booking
    assert fare.total_vnd == 15_000 + 60_000 + 6_000 + 3_000


def test_quote_bike_basic() -> None:
    fare = quote(
        ServiceType.BIKE,
        distance_cm=300_000,  # 3 km
        duration_seconds=600,  # 10 min
    )
    # base 8_000 + 13_500 (3 × 4_500) + 2_000 (10 × 200) + 2_000 booking
    assert fare.total_vnd == 8_000 + 13_500 + 2_000 + 2_000


def test_quote_surge_scales_everything_except_booking() -> None:
    """1.5× surge → base, distance, duration scale; booking stays flat."""
    fare = quote(
        ServiceType.CAR,
        distance_cm=500_000,
        duration_seconds=900,
        surge_bps=15_000,  # 1.5×
    )
    # booking fee must not be multiplied
    assert fare.booking_vnd == 3_000
    assert fare.surge_multiplier == 1.5


def test_quote_minimum_fare_floor() -> None:
    """A tiny trip is rounded up to the per-service minimum."""
    fare = quote(
        ServiceType.CAR,
        distance_cm=10_000,  # 0.1 km
        duration_seconds=30,
    )
    assert fare.total_vnd >= DEFAULT_TARIFFS[ServiceType.CAR].minimum_fare_vnd


def test_quote_validates_distance() -> None:
    with pytest.raises(ValueError, match="distance_cm"):
        quote(ServiceType.CAR, distance_cm=-1, duration_seconds=300)


def test_quote_validates_duration() -> None:
    with pytest.raises(ValueError, match="duration_seconds"):
        quote(ServiceType.CAR, distance_cm=100, duration_seconds=-1)


def test_quote_validates_surge_low() -> None:
    with pytest.raises(ValueError, match="surge_bps"):
        quote(
            ServiceType.CAR,
            distance_cm=100,
            duration_seconds=300,
            surge_bps=MIN_SURGE_BPS - 1,
        )


def test_quote_validates_surge_high() -> None:
    with pytest.raises(ValueError, match="surge_bps"):
        quote(
            ServiceType.CAR,
            distance_cm=100,
            duration_seconds=300,
            surge_bps=MAX_SURGE_BPS + 1,
        )


def test_quote_zero_distance_still_valid() -> None:
    """Distance 0 collapses to base + booking + minimum floor."""
    fare = quote(ServiceType.CAR, distance_cm=0, duration_seconds=0)
    assert fare.total_vnd >= DEFAULT_TARIFFS[ServiceType.CAR].minimum_fare_vnd


def test_quote_surge_increases_total() -> None:
    """Higher surge → higher total (monotone)."""
    base_fare = quote(ServiceType.CAR, distance_cm=500_000, duration_seconds=900)
    surge_fare = quote(
        ServiceType.CAR,
        distance_cm=500_000,
        duration_seconds=900,
        surge_bps=20_000,
    )
    assert surge_fare.total_vnd > base_fare.total_vnd


# ---------- commission_split -----------------------------------------------


def test_commission_split_sums_to_total() -> None:
    fare = make_fare()
    op, drv = commission_split(fare, commission_bps_val=2_000)
    assert op + drv == fare.total_vnd


def test_commission_split_booking_goes_to_operator() -> None:
    """Booking fee is *not* shared — it's fully operator revenue."""
    fare = make_fare(booking_vnd=3_000)
    op, drv = commission_split(fare, commission_bps_val=0)
    # With 0% commission, driver gets the entire ride revenue but no booking.
    assert drv == fare.total_vnd - 3_000
    assert op == 3_000


def test_commission_split_full_commission() -> None:
    """100% commission → driver gets 0 of the ride revenue (booking still to op)."""
    fare = make_fare(booking_vnd=3_000)
    op, drv = commission_split(fare, commission_bps_val=10_000)
    assert drv == 0
    assert op == fare.total_vnd


def test_commission_split_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="commission_bps"):
        commission_split(make_fare(), commission_bps_val=10_001)


def test_default_tariffs_cover_all_services() -> None:
    for service in ServiceType:
        assert service in DEFAULT_TARIFFS


def test_surge_constants() -> None:
    assert MIN_SURGE_BPS == 10_000
    assert MAX_SURGE_BPS == 30_000
