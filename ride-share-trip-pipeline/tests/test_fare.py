"""Fare calculator: base + distance + time + surge."""

from __future__ import annotations

import pytest

from vntrip.fare import DEFAULT_RATE_CARD, compute_fare
from vntrip.schema import VehicleClass


def test_fare_motorbike_short_trip():
    """A 1.5 km, 10 min trip on MOTORBIKE: only base + time, no distance."""
    fb = compute_fare(
        trip_id="T-1",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=1_500,
        ride_seconds=600,
        surge_bps=10_000,
    )
    assert fb.base_fare_vnd == 12_000
    assert fb.distance_fare_vnd == 0  # under the 2-km included
    # 10 minutes × 200 VND = 2_000
    assert fb.time_fare_vnd == 2_000
    assert fb.pre_surge_subtotal_vnd == 14_000
    assert fb.total_fare_vnd == 14_000


def test_fare_motorbike_long_trip():
    """5 km, 15 min trip: 3 km chargeable × 4000 + base + time."""
    fb = compute_fare(
        trip_id="T-2",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=5_000,
        ride_seconds=900,
        surge_bps=10_000,
    )
    # 3000m × 4000 VND/km = 12_000
    assert fb.distance_fare_vnd == 12_000
    assert fb.time_fare_vnd == 3_000  # 15 min × 200
    assert fb.pre_surge_subtotal_vnd == 27_000
    assert fb.total_fare_vnd == 27_000


def test_fare_with_surge_1_5x():
    fb = compute_fare(
        trip_id="T-3",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=5_000,
        ride_seconds=900,
        surge_bps=15_000,
    )
    # 27_000 × 1.5 = 40_500
    assert fb.total_fare_vnd == 40_500
    assert fb.surge_multiplier_bps == 15_000


def test_fare_car_4_higher_rate():
    fb_bike = compute_fare(
        trip_id="T-A",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=5_000,
        ride_seconds=900,
        surge_bps=10_000,
    )
    fb_car = compute_fare(
        trip_id="T-B",
        vehicle_class=VehicleClass.CAR_4,
        distance_m=5_000,
        ride_seconds=900,
        surge_bps=10_000,
    )
    assert fb_car.total_fare_vnd > fb_bike.total_fare_vnd


def test_fare_delivery_no_time_fare():
    """DELIVERY rate has per_minute_vnd=0."""
    fb = compute_fare(
        trip_id="T-D",
        vehicle_class=VehicleClass.DELIVERY,
        distance_m=5_000,
        ride_seconds=900,
        surge_bps=10_000,
    )
    assert fb.time_fare_vnd == 0


def test_fare_rejects_negative_distance():
    with pytest.raises(ValueError, match="distance_m"):
        compute_fare(
            trip_id="T-X",
            vehicle_class=VehicleClass.MOTORBIKE,
            distance_m=-1,
            ride_seconds=900,
            surge_bps=10_000,
        )


def test_fare_rejects_negative_ride_seconds():
    with pytest.raises(ValueError, match="ride_seconds"):
        compute_fare(
            trip_id="T-X",
            vehicle_class=VehicleClass.MOTORBIKE,
            distance_m=5_000,
            ride_seconds=-1,
            surge_bps=10_000,
        )


def test_fare_rejects_low_surge():
    with pytest.raises(ValueError, match="surge_bps"):
        compute_fare(
            trip_id="T-X",
            vehicle_class=VehicleClass.MOTORBIKE,
            distance_m=5_000,
            ride_seconds=900,
            surge_bps=9_999,
        )


def test_fare_zero_distance_zero_time():
    fb = compute_fare(
        trip_id="T-0",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=0,
        ride_seconds=0,
        surge_bps=10_000,
    )
    assert fb.distance_fare_vnd == 0
    assert fb.time_fare_vnd == 0
    assert fb.total_fare_vnd == 12_000  # base only


def test_fare_custom_rate_card():
    """Pass an explicit rate_card."""
    custom = dict(DEFAULT_RATE_CARD)
    # Doubles motorbike base fare
    from vntrip.fare import FareRate

    custom[VehicleClass.MOTORBIKE] = FareRate(
        base_fare_vnd=24_000,
        free_km=2,
        per_km_vnd=4_000,
        per_minute_vnd=200,
    )
    fb = compute_fare(
        trip_id="T-C",
        vehicle_class=VehicleClass.MOTORBIKE,
        distance_m=1_500,
        ride_seconds=600,
        surge_bps=10_000,
        rate_card=custom,
    )
    assert fb.base_fare_vnd == 24_000


def test_fare_banker_rounding_half_even():
    """At exactly half, picks even."""
    # Direct test of the helper
    from vntrip.fare import _banker_div

    assert _banker_div(5, 10) == 0  # 0.5 -> 0 (even)
    assert _banker_div(15, 10) == 2  # 1.5 -> 2 (even)
    assert _banker_div(25, 10) == 2  # 2.5 -> 2 (even)
    assert _banker_div(35, 10) == 4  # 3.5 -> 4 (even)
    assert _banker_div(6, 10) == 1  # 0.6 -> 1
    assert _banker_div(4, 10) == 0  # 0.4 -> 0
