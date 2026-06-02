"""JSONL codec round-trips for every record type."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vntrip.fraud import FraudFinding, FraudKind
from vntrip.io_jsonl import (
    dump_events,
    dump_fares,
    dump_frauds,
    dump_shifts,
    dump_surges,
    dump_trips,
    event_from_dict,
    event_to_dict,
    fare_from_dict,
    fare_to_dict,
    fraud_from_dict,
    fraud_to_dict,
    load_events,
    load_fares,
    load_frauds,
    load_shifts,
    load_surges,
    load_trips,
    shift_from_dict,
    shift_to_dict,
    surge_from_dict,
    surge_to_dict,
    trip_from_dict,
    trip_to_dict,
)
from vntrip.schema import (
    CancelBy,
    DriverShift,
    FareBreakdown,
    SurgeWindow,
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


def test_event_round_trip():
    e = request_event("T-1", "R-1", DEFAULT_TS, surge=12_000)
    assert event_from_dict(event_to_dict(e)) == e


def test_event_round_trip_dropoff():
    e = dropoff_event(
        "T-1", "R-1", "D-1", DEFAULT_TS, distance_m=4_500, fare_vnd=27_000, surge_bps=12_000
    )
    assert event_from_dict(event_to_dict(e)) == e


def test_event_round_trip_cancel():
    e = cancel_event("T-1", "R-1", "D-1", DEFAULT_TS, by=CancelBy.DRIVER)
    out = event_from_dict(event_to_dict(e))
    assert out.cancel_by is CancelBy.DRIVER


def test_event_dump_load_many():
    events = [
        request_event(f"T-{i}", f"R-{i}", DEFAULT_TS + timedelta(minutes=i)) for i in range(10)
    ]
    assert load_events(dump_events(events)) == events


def test_event_dump_newline_terminated():
    e = request_event("T-1", "R-1", DEFAULT_TS)
    text = dump_events([e])
    assert text.endswith("\n")
    assert text.count("\n") == 1


def test_event_load_skips_blank_lines():
    e = request_event("T-1", "R-1", DEFAULT_TS)
    raw = dump_events([e]) + "\n\n   \n"
    [out] = load_events(raw)
    assert out == e


def test_event_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_events("[1, 2]\n")


def test_event_load_rejects_bool_distance():
    text = (
        '{"event_id":"E1","trip_id":"T1","rider_id":"R1","driver_id":"",'
        '"kind":"REQUEST","occurred_at":"2026-05-17T09:00:00+07:00",'
        '"district":"HCM:Q1","vehicle_class":"MOTORBIKE","distance_m":true,'
        '"fare_vnd":0,"surge_bps":10000,"cancel_by":null}\n'
    )
    with pytest.raises(TypeError, match="distance_m must be int"):
        load_events(text)


def test_trip_round_trip_completed():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        accept_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=30)),
        pickup_event("T-1", "R-1", "D-1", DEFAULT_TS + timedelta(seconds=300)),
        dropoff_event(
            "T-1",
            "R-1",
            "D-1",
            DEFAULT_TS + timedelta(seconds=1500),
            distance_m=5_000,
            fare_vnd=30_000,
        ),
    ]
    [t] = stitch(events)
    assert trip_from_dict(trip_to_dict(t)) == t
    assert load_trips(dump_trips([t])) == [t]


def test_trip_round_trip_cancelled():
    events = [
        request_event("T-1", "R-1", DEFAULT_TS),
        cancel_event("T-1", "R-1", "", DEFAULT_TS + timedelta(seconds=20), by=CancelBy.RIDER),
    ]
    [t] = stitch(events)
    out = trip_from_dict(trip_to_dict(t))
    assert out == t


def test_fare_round_trip():
    f = FareBreakdown(
        trip_id="T-1",
        base_fare_vnd=12_000,
        distance_fare_vnd=12_000,
        time_fare_vnd=3_000,
        surge_multiplier_bps=15_000,
        pre_surge_subtotal_vnd=27_000,
        total_fare_vnd=40_500,
    )
    assert fare_from_dict(fare_to_dict(f)) == f
    assert load_fares(dump_fares([f])) == [f]


def test_surge_round_trip():
    sw = SurgeWindow(
        district="HCM:Q1",
        hour_bucket=DEFAULT_TS.isoformat(),
        requests=20,
        completed_trips=8,
        completion_rate_pct=40.0,
        avg_surge_bps=13_000,
    )
    assert surge_from_dict(surge_to_dict(sw)) == sw
    assert load_surges(dump_surges([sw])) == [sw]


def test_surge_rejects_non_number_completion_rate():
    bad = surge_to_dict(
        SurgeWindow(
            district="HCM:Q1",
            hour_bucket=DEFAULT_TS.isoformat(),
            requests=10,
            completed_trips=5,
            completion_rate_pct=50.0,
            avg_surge_bps=12_000,
        )
    )
    bad["completion_rate_pct"] = True
    with pytest.raises(TypeError, match="completion_rate_pct"):
        surge_from_dict(bad)


def test_shift_round_trip():
    s = DriverShift(
        driver_id="D-1",
        shift_date="2026-05-17",
        trips_completed=8,
        trips_cancelled_by_driver=1,
        online_seconds=36_000,
        on_trip_seconds=21_600,
        revenue_vnd=500_000,
    )
    assert shift_from_dict(shift_to_dict(s)) == s
    assert load_shifts(dump_shifts([s])) == [s]


def test_fraud_round_trip():
    f = FraudFinding(
        kind=FraudKind.CANCEL_ABUSE,
        subject_id="D-bad",
        detail="cancelled 27/51 accepts (52.9%), median lag 11s",
        metric=5290,
        trips_affected=27,
    )
    assert fraud_from_dict(fraud_to_dict(f)) == f
    assert load_frauds(dump_frauds([f])) == [f]
