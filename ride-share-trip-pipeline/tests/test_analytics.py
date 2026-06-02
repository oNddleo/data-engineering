"""ETA accuracy + surge windows + driver shifts."""

from __future__ import annotations

from datetime import timedelta

from vntrip.analytics import (
    driver_shifts,
    eta_accuracy_pct,
    eta_accuracy_summary,
    surge_windows,
)
from vntrip.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    accept_event,
    cancel_event,
    dropoff_event,
    pickup_event,
    request_event,
)


def _complete(
    trip_id,
    rider,
    driver,
    request_at,
    *,
    dispatch_s=30,
    wait_s=300,
    ride_s=1200,
    origin="HCM:Q1",
    dest="HCM:Q3",
    distance_m=5_000,
    fare_vnd=30_000,
    surge=10_000,
):  # type: ignore[no-untyped-def]
    accept_at = request_at + timedelta(seconds=dispatch_s)
    pickup_at = request_at + timedelta(seconds=wait_s)
    dropoff_at = pickup_at + timedelta(seconds=ride_s)
    return [
        request_event(trip_id, rider, request_at, district=origin, surge=surge),
        accept_event(trip_id, rider, driver, accept_at, district=origin),
        pickup_event(trip_id, rider, driver, pickup_at, district=origin),
        dropoff_event(
            trip_id,
            rider,
            driver,
            dropoff_at,
            district=dest,
            distance_m=distance_m,
            fare_vnd=fare_vnd,
            surge_bps=surge,
        ),
    ]


# ---------- ETA accuracy ------------------------------------------------------


def test_eta_accuracy_perfect():
    """actual = estimated → 100%."""
    events = _complete("T-1", "R-1", "D-1", DEFAULT_TS, wait_s=300)
    trips = stitch(events)
    ratios = eta_accuracy_pct({"T-1": 300}, trips)
    assert ratios["T-1"] == 100.0


def test_eta_accuracy_overestimate():
    """actual 600s, estimated 300s → 200%."""
    events = _complete("T-2", "R-1", "D-1", DEFAULT_TS, wait_s=600)
    trips = stitch(events)
    ratios = eta_accuracy_pct({"T-2": 300}, trips)
    assert ratios["T-2"] == 200.0


def test_eta_accuracy_skips_cancelled():
    """Cancelled trips (no PICKUP) don't appear in the ratio map."""
    events = [
        request_event("T-3", "R-1", DEFAULT_TS),
        cancel_event(
            "T-3",
            "R-1",
            "",
            DEFAULT_TS + timedelta(seconds=20),
            by=__import__("vntrip.schema", fromlist=["CancelBy"]).CancelBy.RIDER,
        ),
    ]
    trips = stitch(events)
    assert eta_accuracy_pct({"T-3": 300}, trips) == {}


def test_eta_accuracy_summary_percentiles():
    """median / p90 / p99 reported with one decimal."""
    ratios = {f"T-{i}": float(i) for i in range(1, 101)}
    summary = eta_accuracy_summary(ratios)
    # median(1..100) = 50.5 (avg of 50 and 51)
    assert summary["median"] == 50.5
    assert summary["p90"] == 90.0
    assert summary["p99"] == 99.0
    assert summary["n"] == 100.0


def test_eta_accuracy_summary_empty():
    assert eta_accuracy_summary({}) == {"median": 0.0, "p90": 0.0, "p99": 0.0, "n": 0.0}


# ---------- surge windows -----------------------------------------------------


def test_surge_windows_one_district_one_hour():
    """All requests in same district + hour → one window."""
    events = []
    for i in range(5):
        events.extend(
            _complete(
                f"T-{i}",
                f"R-{i}",
                "D-1",
                DEFAULT_TS + timedelta(minutes=i),
                origin="HCM:Q1",
                surge=15_000,
            )
        )
    out = surge_windows(events)
    assert len(out) == 1
    assert out[0].district == "HCM:Q1"
    assert out[0].requests == 5
    assert out[0].completed_trips == 5
    assert out[0].completion_rate_pct == 100.0
    assert out[0].avg_surge_bps == 15_000


def test_surge_window_low_completion_marked_surging():
    """Surge ≥ 1.2× and < 50% completion → ``is_surging``."""
    # 4 requests, only 1 completed
    events = [
        *_complete("T-1", "R-1", "D-1", DEFAULT_TS, surge=15_000),
        request_event("T-2", "R-2", DEFAULT_TS + timedelta(minutes=1), surge=15_000),
        request_event("T-3", "R-3", DEFAULT_TS + timedelta(minutes=2), surge=15_000),
        request_event("T-4", "R-4", DEFAULT_TS + timedelta(minutes=3), surge=15_000),
    ]
    out = surge_windows(events)
    assert len(out) == 1
    assert out[0].is_surging is True


def test_surge_window_completion_rate_blocks_surging():
    """≥ 50% completion → not marked surging even with 1.5× surge."""
    events = []
    for i in range(4):
        events.extend(
            _complete(
                f"T-{i}",
                f"R-{i}",
                "D-1",
                DEFAULT_TS + timedelta(minutes=i),
                surge=15_000,
            )
        )
    out = surge_windows(events)
    assert out[0].is_surging is False  # 100% complete


# ---------- driver shifts -----------------------------------------------------


def test_driver_shifts_one_driver_one_day():
    """Two completed trips for one driver — utilization measured."""
    events = []
    events.extend(
        _complete(
            "T-1", "R-1", "D-1", DEFAULT_TS, dispatch_s=30, wait_s=300, ride_s=600, fare_vnd=20_000
        )
    )
    events.extend(
        _complete(
            "T-2",
            "R-2",
            "D-1",
            DEFAULT_TS + timedelta(hours=1),
            dispatch_s=30,
            wait_s=300,
            ride_s=600,
            fare_vnd=25_000,
        )
    )
    trips = stitch(events)
    [shift] = driver_shifts(trips)
    assert shift.driver_id == "D-1"
    assert shift.trips_completed == 2
    assert shift.revenue_vnd == 45_000
    assert shift.online_seconds > 0
    assert shift.on_trip_seconds > 0
    assert 0 < shift.utilization_pct <= 100


def test_driver_shifts_skip_no_driver():
    """Trips with no driver (cancelled before accept) contribute no shifts."""
    from vntrip.schema import CancelBy

    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        cancel_event("T-1", "R-1", "", DEFAULT_TS + timedelta(seconds=20), by=CancelBy.RIDER),
    ]
    assert driver_shifts(stitch(events)) == []


def test_driver_shifts_two_days_distinct_shifts():
    """Same driver on two days → two shifts."""
    events = []
    events.extend(_complete("T-1", "R-1", "D-1", DEFAULT_TS, fare_vnd=20_000))
    events.extend(_complete("T-2", "R-2", "D-1", DEFAULT_TS + timedelta(days=1), fare_vnd=25_000))
    shifts = driver_shifts(stitch(events))
    assert len(shifts) == 2
    assert {s.shift_date for s in shifts} == {"2026-05-17", "2026-05-18"}
