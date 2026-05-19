"""Schema validation: ParcelEvent, Parcel, CourierSLA."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from vnpost.schema import (
    CourierCode,
    CourierSLA,
    Parcel,
    ParcelEventKind,
    ParcelStatus,
)

from ._fixtures import DEFAULT_TS, make_event


def test_event_kinds_complete():
    assert {k.value for k in ParcelEventKind} == {
        "CREATED",
        "PICKED_UP",
        "IN_TRANSIT",
        "AT_HUB",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "RETURN_TO_SENDER",
        "EXCEPTION",
    }


def test_parcel_status_six_values():
    assert {s.value for s in ParcelStatus} == {
        "PENDING",
        "IN_FLIGHT",
        "DELIVERED",
        "RETURNED",
        "LOST",
        "EXCEPTION",
    }


def test_courier_code_five_majors():
    assert {c.value for c in CourierCode} == {
        "VTP",
        "GHN",
        "GHTK",
        "JT",
        "SPX",
    }


def test_event_basic_ok():
    e = make_event()
    assert e.tracking_id == "T-0001"
    assert e.kind is ParcelEventKind.CREATED


def test_event_rejects_empty_id():
    with pytest.raises(ValueError, match="event_id must be non-empty"):
        make_event(event_id="")


def test_event_rejects_empty_tracking_id():
    with pytest.raises(ValueError, match="tracking_id must be non-empty"):
        make_event(tracking_id="")


def test_event_rejects_naive_datetime():
    with pytest.raises(ValueError, match="must be timezone-aware"):
        make_event(occurred_at=datetime(2026, 5, 18, 9, 0, 0))


# ---------- Parcel -----------------------------------------------------------


def _parcel(**overrides) -> Parcel:  # type: ignore[no-untyped-def]
    defaults = {
        "tracking_id": "T-1",
        "courier": CourierCode.GHN,
        "status": ParcelStatus.DELIVERED,
        "created_at": DEFAULT_TS,
        "picked_up_at": DEFAULT_TS + timedelta(hours=1),
        "delivered_at": DEFAULT_TS + timedelta(hours=48),
        "returned_at": None,
        "last_event_at": DEFAULT_TS + timedelta(hours=48),
        "n_events": 6,
        "n_hubs_visited": 3,
        "origin_hub": "HCM-TPN",
        "dest_hub": "HN-CG",
    }
    defaults.update(overrides)
    return Parcel(**defaults)


def test_parcel_is_delivered():
    p = _parcel(status=ParcelStatus.DELIVERED)
    assert p.is_delivered
    assert not p.is_returned


def test_parcel_transit_hours_computed():
    p = _parcel()
    assert p.transit_hours == 47  # 48h pickup→delivered minus 1h pickup offset


def test_parcel_transit_hours_minus_one_when_not_delivered():
    p = _parcel(status=ParcelStatus.IN_FLIGHT, delivered_at=None)
    assert p.transit_hours == -1


# ---------- CourierSLA -------------------------------------------------------


def test_sla_basic():
    s = CourierSLA(
        courier=CourierCode.GHN,
        n_parcels=100,
        n_delivered=95,
        n_on_time=85,
        median_transit_hours=48,
        p95_transit_hours=80,
        on_time_rate_pct=89.5,
    )
    assert s.delivery_rate_pct == 95.0


def test_sla_zero_parcels_zero_delivery_rate():
    s = CourierSLA(
        courier=CourierCode.GHN,
        n_parcels=0,
        n_delivered=0,
        n_on_time=0,
        median_transit_hours=0,
        p95_transit_hours=0,
        on_time_rate_pct=0.0,
    )
    assert s.delivery_rate_pct == 0.0


def test_sla_rejects_on_time_gt_delivered():
    with pytest.raises(ValueError, match="n_on_time"):
        CourierSLA(
            courier=CourierCode.GHN,
            n_parcels=10,
            n_delivered=5,
            n_on_time=8,
            median_transit_hours=0,
            p95_transit_hours=0,
            on_time_rate_pct=0.0,
        )


def test_sla_rejects_delivered_gt_parcels():
    with pytest.raises(ValueError, match="n_delivered"):
        CourierSLA(
            courier=CourierCode.GHN,
            n_parcels=5,
            n_delivered=10,
            n_on_time=0,
            median_transit_hours=0,
            p95_transit_hours=0,
            on_time_rate_pct=0.0,
        )
