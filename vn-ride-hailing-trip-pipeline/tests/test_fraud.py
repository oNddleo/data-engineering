"""Fraud detection: ghost rides, cancellation abuse, surge gaming."""

from __future__ import annotations

from datetime import datetime

import pytest

from vnride.fraud import (
    FraudKind,
    find_cancellation_abuse,
    find_ghost_rides,
    find_surge_gaming,
)
from vnride.schema import VN_TZ, ServiceType

from ._fixtures import make_cancelled, make_completed, make_fare

# ---------- ghost rides -----------------------------------------------------


def test_ghost_ride_fires_on_tiny_trip() -> None:
    """A 5 m / 10 s COMPLETED trip is a ghost ride."""
    t = make_completed(
        distance_cm=500,
        duration_seconds=10,
    )
    findings = find_ghost_rides([t])
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.GHOST_RIDE


def test_ghost_ride_silent_on_normal_trip() -> None:
    """Default 5 km / 15 min trip is not a ghost ride."""
    t = make_completed()
    assert find_ghost_rides([t]) == []


def test_ghost_ride_silent_on_just_above_distance() -> None:
    """Just above the threshold should not fire."""
    t = make_completed(distance_cm=10_001, duration_seconds=10)
    assert find_ghost_rides([t]) == []


def test_ghost_ride_silent_on_just_above_duration() -> None:
    t = make_completed(distance_cm=500, duration_seconds=31)
    assert find_ghost_rides([t]) == []


def test_ghost_ride_ignores_non_completed() -> None:
    """A tiny CANCELLED trip is not a ghost ride."""
    t = make_cancelled()
    assert find_ghost_rides([t]) == []


def test_ghost_ride_custom_thresholds() -> None:
    """Loosen the thresholds and a 50 m / 60 s trip qualifies."""
    t = make_completed(distance_cm=5_000, duration_seconds=60)
    findings = find_ghost_rides(
        [t],
        max_distance_cm=10_000,
        max_duration_seconds=120,
    )
    assert len(findings) == 1


def test_ghost_ride_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError):
        find_ghost_rides([], max_distance_cm=-1)


# ---------- cancellation abuse ---------------------------------------------


def test_cancel_abuse_fires_at_threshold() -> None:
    """A driver with 15/30 = 50% cancellations on 30 trips fires."""
    trips = []
    for i in range(15):
        trips.append(make_completed(trip_id=f"C-{i}", driver_id="D-1"))
    for i in range(15):
        trips.append(make_cancelled(trip_id=f"X-{i}", driver_id="D-1"))
    findings = find_cancellation_abuse(trips, min_trips=20, min_cancel_rate=0.50)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.CANCELLATION_ABUSE


def test_cancel_abuse_silent_below_volume() -> None:
    """Even 100% cancel rate doesn't fire if total trips < min_trips."""
    trips = [make_cancelled(trip_id=f"X-{i}", driver_id="D-1") for i in range(3)]
    assert find_cancellation_abuse(trips, min_trips=20) == []


def test_cancel_abuse_silent_below_rate() -> None:
    """Plenty of trips but only 10% cancel — not abuse."""
    trips = [make_completed(trip_id=f"C-{i}", driver_id="D-1") for i in range(45)] + [
        make_cancelled(trip_id=f"X-{i}", driver_id="D-1") for i in range(5)
    ]
    assert find_cancellation_abuse(trips, min_trips=20) == []


def test_cancel_abuse_validates_params() -> None:
    with pytest.raises(ValueError, match="min_trips"):
        find_cancellation_abuse([], min_trips=0)
    with pytest.raises(ValueError, match="min_cancel_rate"):
        find_cancellation_abuse([], min_cancel_rate=1.5)


def test_cancel_abuse_ignores_no_driver() -> None:
    """NO_DRIVER trips don't count toward any driver's stats."""
    trips = [make_completed(trip_id=f"C-{i}", driver_id="D-1") for i in range(25)]
    assert find_cancellation_abuse(trips) == []


# ---------- surge gaming ----------------------------------------------------


def test_surge_gaming_fires_on_repeated_surge_pair() -> None:
    """5 surge trips between the same rider+driver fire."""
    trips = [
        make_completed(
            trip_id=f"S-{i}",
            rider_id="R-1",
            driver_id="D-1",
            fare=make_fare(surge_multiplier_bps=14_000),
        )
        for i in range(5)
    ]
    findings = find_surge_gaming(trips)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.SURGE_GAMING
    assert findings[0].metric == 5


def test_surge_gaming_silent_when_any_non_surge() -> None:
    """If even one trip in the pair is non-surge, no finding."""
    trips = [
        make_completed(
            trip_id=f"S-{i}",
            rider_id="R-1",
            driver_id="D-1",
            fare=make_fare(surge_multiplier_bps=14_000),
        )
        for i in range(4)
    ]
    trips.append(
        make_completed(
            trip_id="N-1",
            rider_id="R-1",
            driver_id="D-1",
            fare=make_fare(surge_multiplier_bps=10_000),  # no surge
        )
    )
    assert find_surge_gaming(trips) == []


def test_surge_gaming_silent_below_threshold() -> None:
    """Only 4 shared surge trips, below default 5."""
    trips = [
        make_completed(
            trip_id=f"S-{i}",
            rider_id="R-1",
            driver_id="D-1",
            fare=make_fare(surge_multiplier_bps=14_000),
        )
        for i in range(4)
    ]
    assert find_surge_gaming(trips) == []


def test_surge_gaming_separates_by_operator() -> None:
    """Two operators × same rider+driver = two separate keys."""
    trips_grab = [
        make_completed(
            trip_id=f"G-{i}",
            rider_id="R-1",
            driver_id="D-1",
            operator="GRAB",
            fare=make_fare(surge_multiplier_bps=14_000),
        )
        for i in range(3)
    ]
    trips_be = [
        make_completed(
            trip_id=f"B-{i}",
            rider_id="R-1",
            driver_id="D-1",
            operator="BE",
            fare=make_fare(surge_multiplier_bps=14_000),
        )
        for i in range(3)
    ]
    # Each group has 3 trips, less than default 5 → no finding.
    assert find_surge_gaming(trips_grab + trips_be) == []


def test_surge_gaming_validates_param() -> None:
    with pytest.raises(ValueError, match="min_surge_trips"):
        find_surge_gaming([], min_surge_trips=1)


def test_surge_gaming_lower_threshold() -> None:
    """Lowering the threshold makes a small repeated-pair fire."""
    trips = [
        make_completed(
            trip_id=f"S-{i}",
            rider_id="R-1",
            driver_id="D-1",
            fare=make_fare(surge_multiplier_bps=12_000),
        )
        for i in range(3)
    ]
    findings = find_surge_gaming(trips, min_surge_trips=2)
    assert len(findings) == 1


def test_finding_kinds_complete() -> None:
    assert {k.value for k in FraudKind} == {
        "GHOST_RIDE",
        "CANCELLATION_ABUSE",
        "SURGE_GAMING",
    }


# ---------- helpers used by other tests ------------------------------------


def test_ghost_ride_uses_requested_at_irrelevant() -> None:
    """Different requested_at values do not affect ghost detection."""
    t1 = make_completed(
        trip_id="T-1",
        distance_cm=100,
        duration_seconds=5,
        requested_at=datetime(2026, 5, 18, 8, 0, tzinfo=VN_TZ),
    )
    t2 = make_completed(
        trip_id="T-2",
        distance_cm=100,
        duration_seconds=5,
        service=ServiceType.BIKE,
        requested_at=datetime(2026, 5, 18, 22, 0, tzinfo=VN_TZ),
    )
    findings = find_ghost_rides([t1, t2])
    assert len(findings) == 2
