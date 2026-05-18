"""Cancel-abuse + phantom-trip detection."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vntrip.fraud import (
    FraudKind,
    find_cancel_abuse,
    find_phantom_trips,
)
from vntrip.schema import CancelBy
from vntrip.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    accept_event,
    cancel_event,
    dropoff_event,
    pickup_event,
    request_event,
)


def _make_driver_cancel(trip_id: str, driver: str, request_at, lag_seconds: int = 5):  # type: ignore[no-untyped-def]
    accept_at = request_at + timedelta(seconds=30)
    return [
        request_event(trip_id, f"R-{trip_id}", request_at),
        accept_event(trip_id, f"R-{trip_id}", driver, accept_at),
        cancel_event(
            trip_id,
            f"R-{trip_id}",
            driver,
            accept_at + timedelta(seconds=lag_seconds),
            by=CancelBy.DRIVER,
        ),
    ]


def _make_completion(
    trip_id: str, driver: str, request_at, *, distance_m: int = 5_000, ride_seconds: int = 1200
):  # type: ignore[no-untyped-def]
    accept_at = request_at + timedelta(seconds=30)
    pickup_at = request_at + timedelta(seconds=300)
    dropoff_at = pickup_at + timedelta(seconds=ride_seconds)
    return [
        request_event(trip_id, f"R-{trip_id}", request_at),
        accept_event(trip_id, f"R-{trip_id}", driver, accept_at),
        pickup_event(trip_id, f"R-{trip_id}", driver, pickup_at),
        dropoff_event(
            trip_id, f"R-{trip_id}", driver, dropoff_at, distance_m=distance_m, fare_vnd=30_000
        ),
    ]


# ---------- cancel abuse ------------------------------------------------------


def test_cancel_abuse_high_rate_short_lag_flagged():
    """Driver with 100% cancel rate at 5s lag → flagged."""
    events = []
    for i in range(15):
        events.extend(
            _make_driver_cancel(
                f"T-{i:03d}",
                "D-bad",
                DEFAULT_TS + timedelta(minutes=i),
                lag_seconds=5,
            )
        )
    trips = stitch(events)
    findings = find_cancel_abuse(trips, min_accepts=10)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.CANCEL_ABUSE
    assert findings[0].subject_id == "D-bad"


def test_cancel_abuse_long_lag_not_flagged():
    """Cancel-rate is high, but lag is long → not flagged."""
    events = []
    for i in range(15):
        events.extend(
            _make_driver_cancel(
                f"T-{i:03d}",
                "D-slow",
                DEFAULT_TS + timedelta(minutes=i),
                lag_seconds=200,  # > 30s default threshold
            )
        )
    findings = find_cancel_abuse(stitch(events), min_accepts=10)
    assert findings == []


def test_cancel_abuse_low_rate_not_flagged():
    """Driver completes most trips → not flagged."""
    events = []
    for i in range(12):
        events.extend(
            _make_completion(
                f"TC-{i:03d}",
                "D-good",
                DEFAULT_TS + timedelta(minutes=i),
            )
        )
    for i in range(3):
        events.extend(
            _make_driver_cancel(
                f"TX-{i:03d}",
                "D-good",
                DEFAULT_TS + timedelta(hours=2, minutes=i),
                lag_seconds=5,
            )
        )
    findings = find_cancel_abuse(stitch(events), min_accepts=10)
    assert findings == []  # 3/15 = 20%, below 30% threshold


def test_cancel_abuse_below_min_accepts_skipped():
    """Driver with < min_accepts is skipped (too small)."""
    events = []
    for i in range(5):
        events.extend(
            _make_driver_cancel(
                f"T-{i:03d}",
                "D-tiny",
                DEFAULT_TS + timedelta(minutes=i),
            )
        )
    assert find_cancel_abuse(stitch(events), min_accepts=10) == []


def test_cancel_abuse_rejects_invalid_args():
    with pytest.raises(ValueError):
        find_cancel_abuse([], min_accepts=0)
    with pytest.raises(ValueError):
        find_cancel_abuse([], max_cancel_rate_pct=101)
    with pytest.raises(ValueError):
        find_cancel_abuse([], max_accept_to_cancel_seconds=0)


# ---------- phantom trips -----------------------------------------------------


def test_phantom_trip_short_distance_flagged():
    """Completion with distance < 200m → flagged."""
    events = _make_completion(
        "T-1",
        "D-1",
        DEFAULT_TS,
        distance_m=50,
        ride_seconds=600,
    )
    findings = find_phantom_trips(stitch(events))
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.PHANTOM_TRIP
    assert findings[0].subject_id == "D-1"


def test_phantom_trip_short_duration_flagged():
    """Completion with ride < 30s → flagged."""
    events = _make_completion(
        "T-1",
        "D-1",
        DEFAULT_TS,
        distance_m=5_000,
        ride_seconds=10,
    )
    findings = find_phantom_trips(stitch(events))
    assert len(findings) == 1


def test_phantom_trip_normal_not_flagged():
    """Normal completion → not flagged."""
    events = _make_completion(
        "T-1",
        "D-1",
        DEFAULT_TS,
        distance_m=5_000,
        ride_seconds=600,
    )
    assert find_phantom_trips(stitch(events)) == []


def test_phantom_trip_aggregates_per_driver():
    """Multiple phantom trips on one driver → one finding with count."""
    events = []
    for i in range(5):
        events.extend(
            _make_completion(
                f"T-{i:03d}",
                "D-bad",
                DEFAULT_TS + timedelta(minutes=i),
                distance_m=50,
                ride_seconds=10,
            )
        )
    findings = find_phantom_trips(stitch(events))
    assert len(findings) == 1
    assert findings[0].trips_affected == 5


def test_phantom_trip_skips_cancelled():
    """Cancelled trips with no DROPOFF can't be phantom completions."""
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        cancel_event("T-1", "R-1", "", DEFAULT_TS + timedelta(seconds=20), by=CancelBy.RIDER),
    ]
    assert find_phantom_trips(stitch(events)) == []


def test_phantom_trip_rejects_invalid_args():
    with pytest.raises(ValueError):
        find_phantom_trips([], min_distance_m=0)
    with pytest.raises(ValueError):
        find_phantom_trips([], min_ride_seconds=0)
