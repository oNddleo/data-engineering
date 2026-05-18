"""Hypothesis properties — invariants of fare + state machine + analytics."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vntrip.fare import compute_fare
from vntrip.schema import TripEventKind, VehicleClass
from vntrip.simulator import generate
from vntrip.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    accept_event,
    dropoff_event,
    pickup_event,
    request_event,
)


@given(
    distance_m=st.integers(min_value=0, max_value=100_000),
    ride_seconds=st.integers(min_value=0, max_value=14_400),
    surge_bps=st.integers(min_value=10_000, max_value=30_000),
    vehicle=st.sampled_from(list(VehicleClass)),
)
@settings(max_examples=80)
def test_property_fare_components_non_negative(
    distance_m: int,
    ride_seconds: int,
    surge_bps: int,
    vehicle: VehicleClass,
) -> None:
    """Every fare component is in [0, total_fare_vnd]."""
    fb = compute_fare(
        trip_id="T-prop",
        vehicle_class=vehicle,
        distance_m=distance_m,
        ride_seconds=ride_seconds,
        surge_bps=surge_bps,
    )
    assert fb.base_fare_vnd >= 0
    assert fb.distance_fare_vnd >= 0
    assert fb.time_fare_vnd >= 0
    assert fb.pre_surge_subtotal_vnd >= fb.base_fare_vnd
    assert fb.total_fare_vnd >= fb.base_fare_vnd  # surge >= 1.0 → total >= pre_surge >= base


@given(
    distance_m=st.integers(min_value=0, max_value=50_000),
    ride_seconds=st.integers(min_value=0, max_value=7_200),
    surge_bps=st.integers(min_value=10_000, max_value=30_000),
    vehicle=st.sampled_from(list(VehicleClass)),
)
@settings(max_examples=80)
def test_property_surge_monotonic(
    distance_m: int,
    ride_seconds: int,
    surge_bps: int,
    vehicle: VehicleClass,
) -> None:
    """A higher surge multiplier never produces a smaller total fare."""
    low = compute_fare(
        trip_id="T-low",
        vehicle_class=vehicle,
        distance_m=distance_m,
        ride_seconds=ride_seconds,
        surge_bps=10_000,
    )
    high = compute_fare(
        trip_id="T-high",
        vehicle_class=vehicle,
        distance_m=distance_m,
        ride_seconds=ride_seconds,
        surge_bps=surge_bps,
    )
    assert high.total_fare_vnd >= low.total_fare_vnd


@given(
    distance_m=st.integers(min_value=0, max_value=50_000),
    ride_seconds=st.integers(min_value=0, max_value=7_200),
    vehicle=st.sampled_from(list(VehicleClass)),
)
@settings(max_examples=50)
def test_property_no_surge_means_pre_equals_total(
    distance_m: int,
    ride_seconds: int,
    vehicle: VehicleClass,
) -> None:
    """``surge_bps == 10_000`` → ``total_fare_vnd == pre_surge_subtotal_vnd``."""
    fb = compute_fare(
        trip_id="T-1",
        vehicle_class=vehicle,
        distance_m=distance_m,
        ride_seconds=ride_seconds,
        surge_bps=10_000,
    )
    assert fb.total_fare_vnd == fb.pre_surge_subtotal_vnd


@given(
    dispatch_s=st.integers(min_value=10, max_value=300),
    wait_extra_s=st.integers(min_value=60, max_value=1_200),
    ride_s=st.integers(min_value=60, max_value=3_600),
    distance_m=st.integers(min_value=200, max_value=50_000),
)
@settings(max_examples=30)
def test_property_completed_trip_stitches(
    dispatch_s: int,
    wait_extra_s: int,
    ride_s: int,
    distance_m: int,
) -> None:
    """A well-formed completed sequence always produces one ``Trip``."""
    request_at = DEFAULT_TS
    accept_at = request_at + timedelta(seconds=dispatch_s)
    pickup_at = accept_at + timedelta(seconds=wait_extra_s)
    dropoff_at = pickup_at + timedelta(seconds=ride_s)
    events = [
        request_event("T-P", "R-P", request_at),
        accept_event("T-P", "R-P", "D-P", accept_at),
        pickup_event("T-P", "R-P", "D-P", pickup_at),
        dropoff_event("T-P", "R-P", "D-P", dropoff_at, distance_m=distance_m, fare_vnd=50_000),
    ]
    [t] = stitch(events)
    assert t.is_completed
    assert t.ride_seconds == ride_s
    assert t.dispatch_seconds == dispatch_s


@given(
    n_riders=st.integers(min_value=5, max_value=40),
    n_drivers=st.integers(min_value=2, max_value=15),
    n_days=st.integers(min_value=2, max_value=8),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_simulator_output_stitches_cleanly(
    n_riders: int,
    n_drivers: int,
    n_days: int,
    seed: int,
) -> None:
    """The simulator never emits invalid state-machine sequences."""
    events = generate(n_riders=n_riders, n_drivers=n_drivers, n_days=n_days, seed=seed)
    trips = stitch(events)
    # one trip per REQUEST event
    n_requests = sum(1 for e in events if e.kind is TripEventKind.REQUEST)
    assert len(trips) == n_requests


@given(
    n_riders=st.integers(min_value=5, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_stitched_trips_sorted(n_riders: int, seed: int) -> None:
    """Stitched trips are sorted by (requested_at, trip_id)."""
    events = generate(n_riders=n_riders, n_drivers=5, n_days=3, seed=seed)
    out = stitch(events)
    keys = [(t.requested_at, t.trip_id) for t in out]
    assert keys == sorted(keys)


@given(
    n_riders=st.integers(min_value=5, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_completed_trip_has_driver(n_riders: int, seed: int) -> None:
    """A completed trip always has a non-empty driver_id."""
    events = generate(n_riders=n_riders, n_drivers=5, n_days=3, seed=seed)
    for t in stitch(events):
        if t.is_completed:
            assert t.driver_id
            assert t.fare_vnd > 0
            assert t.distance_m > 0
