"""TripEvent / Trip / FareBreakdown / SurgeWindow / DriverShift validation."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from vntrip.schema import (
    CancelBy,
    DriverShift,
    FareBreakdown,
    SurgeWindow,
    Trip,
    TripEventKind,
    VehicleClass,
)

from ._fixtures import DEFAULT_TS, make_event


def test_event_kinds_complete():
    assert {k.value for k in TripEventKind} == {
        "REQUEST",
        "ACCEPT",
        "PICKUP",
        "DROPOFF",
        "CANCEL",
        "EXPIRE",
        "SURGE_UPDATE",
    }


def test_event_request_default_ok():
    e = make_event()
    assert e.kind is TripEventKind.REQUEST
    assert e.fare_vnd == 0
    assert e.surge_bps == 10_000


def test_event_dropoff_requires_fare():
    with pytest.raises(ValueError, match="DROPOFF must have fare_vnd > 0"):
        make_event(
            event_id="E-2",
            kind=TripEventKind.DROPOFF,
            driver_id="D-1",
            fare_vnd=0,
            distance_m=5_000,
        )


def test_event_dropoff_with_fare_ok():
    e = make_event(
        event_id="E-2",
        kind=TripEventKind.DROPOFF,
        driver_id="D-1",
        fare_vnd=30_000,
        distance_m=5_000,
    )
    assert e.fare_vnd == 30_000


def test_event_non_dropoff_rejects_fare():
    with pytest.raises(ValueError, match="fare_vnd must be 0"):
        make_event(kind=TripEventKind.REQUEST, fare_vnd=100)


def test_event_cancel_requires_cancel_by():
    with pytest.raises(ValueError, match="CANCEL events must set cancel_by"):
        make_event(
            event_id="E-3",
            kind=TripEventKind.CANCEL,
            driver_id="D-1",
            cancel_by=None,
        )


def test_event_non_cancel_rejects_cancel_by():
    with pytest.raises(ValueError, match="cancel_by must be None"):
        make_event(kind=TripEventKind.REQUEST, cancel_by=CancelBy.RIDER)


def test_event_driver_required_on_accept():
    with pytest.raises(ValueError, match="driver_id must be set"):
        make_event(
            event_id="E-4",
            kind=TripEventKind.ACCEPT,
            driver_id="",
        )


def test_event_surge_must_be_at_least_10000():
    with pytest.raises(ValueError, match="surge_bps must be >= 10000"):
        make_event(surge_bps=9_999)


def test_event_negative_fare_rejected():
    with pytest.raises(ValueError, match="fare_vnd must be >= 0"):
        make_event(kind=TripEventKind.DROPOFF, driver_id="D-1", fare_vnd=-1, distance_m=5_000)


def test_event_negative_distance_rejected():
    with pytest.raises(ValueError, match="distance_m must be >= 0"):
        make_event(distance_m=-1)


def test_event_naive_datetime_rejected():
    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        make_event(occurred_at=datetime(2026, 5, 17, 9, 0, 0))


# ---------- Trip --------------------------------------------------------------


def test_trip_wait_seconds_computed():
    t = Trip(
        trip_id="T-1",
        rider_id="R-1",
        driver_id="D-1",
        vehicle_class=VehicleClass.MOTORBIKE,
        origin_district="HCM:Q1",
        dest_district="HCM:Q3",
        requested_at=DEFAULT_TS,
        accepted_at=DEFAULT_TS + timedelta(seconds=30),
        picked_up_at=DEFAULT_TS + timedelta(seconds=300),
        dropped_off_at=DEFAULT_TS + timedelta(seconds=1500),
        cancelled_at=None,
        cancel_by=None,
        distance_m=5_000,
        fare_vnd=30_000,
        surge_bps=10_000,
    )
    assert t.wait_seconds == 300
    assert t.dispatch_seconds == 30
    assert t.ride_seconds == 1200
    assert t.is_completed is True
    assert t.is_cancelled is False


def test_trip_pending_uses_sentinel():
    t = Trip(
        trip_id="T-2",
        rider_id="R-1",
        driver_id="",
        vehicle_class=VehicleClass.MOTORBIKE,
        origin_district="HCM:Q1",
        dest_district="",
        requested_at=DEFAULT_TS,
        accepted_at=None,
        picked_up_at=None,
        dropped_off_at=None,
        cancelled_at=None,
        cancel_by=None,
        distance_m=0,
        fare_vnd=0,
        surge_bps=10_000,
    )
    assert t.wait_seconds == -1
    assert t.ride_seconds == -1
    assert t.dispatch_seconds == -1
    assert t.is_completed is False


# ---------- FareBreakdown -----------------------------------------------------


def test_fare_breakdown_validates_positive():
    with pytest.raises(ValueError, match="base_fare_vnd"):
        FareBreakdown(
            trip_id="T-1",
            base_fare_vnd=-1,
            distance_fare_vnd=0,
            time_fare_vnd=0,
            surge_multiplier_bps=10_000,
            pre_surge_subtotal_vnd=0,
            total_fare_vnd=0,
        )


def test_fare_breakdown_rejects_low_surge():
    with pytest.raises(ValueError, match="surge_multiplier_bps"):
        FareBreakdown(
            trip_id="T-1",
            base_fare_vnd=10_000,
            distance_fare_vnd=0,
            time_fare_vnd=0,
            surge_multiplier_bps=9_999,
            pre_surge_subtotal_vnd=10_000,
            total_fare_vnd=10_000,
        )


# ---------- SurgeWindow -------------------------------------------------------


def test_surge_window_is_surging_threshold():
    sw = SurgeWindow(
        district="HCM:Q1",
        hour_bucket=DEFAULT_TS.isoformat(),
        requests=20,
        completed_trips=8,
        completion_rate_pct=40.0,
        avg_surge_bps=13_000,
    )
    assert sw.is_surging is True


def test_surge_window_not_surging_when_complete():
    sw = SurgeWindow(
        district="HCM:Q1",
        hour_bucket=DEFAULT_TS.isoformat(),
        requests=20,
        completed_trips=18,
        completion_rate_pct=90.0,
        avg_surge_bps=15_000,
    )
    assert sw.is_surging is False


def test_surge_window_not_surging_no_surge():
    sw = SurgeWindow(
        district="HCM:Q1",
        hour_bucket=DEFAULT_TS.isoformat(),
        requests=10,
        completed_trips=2,
        completion_rate_pct=20.0,
        avg_surge_bps=10_000,
    )
    assert sw.is_surging is False


# ---------- DriverShift -------------------------------------------------------


def test_driver_shift_utilization():
    s = DriverShift(
        driver_id="D-1",
        shift_date="2026-05-17",
        trips_completed=8,
        trips_cancelled_by_driver=1,
        online_seconds=10 * 3600,
        on_trip_seconds=6 * 3600,
        revenue_vnd=500_000,
    )
    assert s.utilization_pct == 60.0


def test_driver_shift_zero_online_returns_zero():
    s = DriverShift(
        driver_id="D-1",
        shift_date="2026-05-17",
        trips_completed=0,
        trips_cancelled_by_driver=0,
        online_seconds=0,
        on_trip_seconds=0,
        revenue_vnd=0,
    )
    assert s.utilization_pct == 0.0
