"""Trip state machine: validate_trip_events + stitch."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vntrip.schema import CancelBy, TripEventKind, VehicleClass
from vntrip.state import stitch, validate_trip_events

from ._fixtures import (
    DEFAULT_TS,
    accept_event,
    cancel_event,
    dropoff_event,
    expire_event,
    pickup_event,
    request_event,
)

# ---------- validate_trip_events ---------------------------------------------


def test_validate_empty_rejects():
    with pytest.raises(ValueError, match="empty event list"):
        validate_trip_events([])


def test_validate_must_start_with_request():
    events = [accept_event("T-1", "R-1", "D-1", DEFAULT_TS)]
    with pytest.raises(ValueError, match="does not start with REQUEST"):
        validate_trip_events(events)


def test_validate_happy_path():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        pickup_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=300)),
        dropoff_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=1500)),
    ]
    validate_trip_events(events)  # no raise


def test_validate_rejects_dropoff_without_pickup():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        dropoff_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=1500)),
    ]
    with pytest.raises(ValueError, match="illegal ACCEPT → DROPOFF"):
        validate_trip_events(events)


def test_validate_rejects_post_terminal_event():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        cancel_event("T-1", "R-1", "", DEFAULT_TS + timedelta(seconds=30), by=CancelBy.RIDER),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=60)),
    ]
    with pytest.raises(ValueError, match="after terminal"):
        validate_trip_events(events)


def test_validate_cancel_after_accept_ok():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        cancel_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=45), by=CancelBy.DRIVER),
    ]
    validate_trip_events(events)


def test_validate_cancel_after_pickup_ok():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        pickup_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=300)),
        cancel_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=400), by=CancelBy.RIDER),
    ]
    validate_trip_events(events)


def test_validate_expire_after_request_ok():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        expire_event("T-1", "R-1", DEFAULT_TS + timedelta(minutes=5)),
    ]
    validate_trip_events(events)


def test_validate_expire_after_accept_rejected():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        expire_event("T-1", "R-1", DEFAULT_TS + timedelta(seconds=60)),
    ]
    with pytest.raises(ValueError, match="illegal ACCEPT → EXPIRE"):
        validate_trip_events(events)


# ---------- stitch ------------------------------------------------------------


def test_stitch_completed_trip():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS, district="HCM:Q1"),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        pickup_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=300)),
        dropoff_event(
            "T-1",
            "R-1",
            "D-1",
            DEFAULT_TS + timedelta(seconds=1500),
            district="HCM:Q3",
            distance_m=4_500,
            fare_vnd=25_000,
        ),
    ]
    [t] = stitch(events)
    assert t.trip_id == "T-1"
    assert t.is_completed is True
    assert t.origin_district == "HCM:Q1"
    assert t.dest_district == "HCM:Q3"
    assert t.distance_m == 4_500
    assert t.fare_vnd == 25_000
    assert t.driver_id == "D-1"


def test_stitch_cancelled_trip():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        cancel_event("T-1", "R-1", "", DEFAULT_TS + timedelta(seconds=20), by=CancelBy.RIDER),
    ]
    [t] = stitch(events)
    assert t.is_cancelled is True
    assert t.is_completed is False
    assert t.cancel_by is CancelBy.RIDER
    assert t.driver_id == ""


def test_stitch_expired_trip():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        expire_event("T-1", "R-1", DEFAULT_TS + timedelta(minutes=5)),
    ]
    [t] = stitch(events)
    assert t.is_cancelled is True  # treated as cancellation for analytics
    assert t.cancel_by is CancelBy.SYSTEM


def test_stitch_multiple_trips_sorted_by_request_time():
    events = [
        request_event("T-A", "R-1", DEFAULT_TS + timedelta(hours=2)),
        request_event("T-B", "R-2", DEFAULT_TS),
        request_event("T-C", "R-3", DEFAULT_TS + timedelta(hours=1)),
    ]
    out = stitch(events)
    assert [t.trip_id for t in out] == ["T-B", "T-C", "T-A"]


def test_stitch_filters_surge_updates():
    from vntrip.schema import TripEvent

    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        TripEvent(
            event_id="SU-1",
            trip_id="SU-X",
            rider_id="",
            driver_id="",
            kind=TripEventKind.SURGE_UPDATE,
            occurred_at=DEFAULT_TS,
            district="",
            vehicle_class=VehicleClass.MOTORBIKE,
            surge_bps=15_000,
        ),
        expire_event("T-1", "R-1", DEFAULT_TS + timedelta(minutes=5)),
    ]
    out = stitch(events)
    assert len(out) == 1
    assert out[0].trip_id == "T-1"
