"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vnpost.fraud import FraudFinding, FraudKind
from vnpost.io_jsonl import (
    dump_events,
    dump_frauds,
    dump_parcels,
    dump_slas,
    event_from_dict,
    event_to_dict,
    fraud_from_dict,
    fraud_to_dict,
    load_events,
    load_frauds,
    load_parcels,
    load_slas,
    parcel_from_dict,
    parcel_to_dict,
    sla_from_dict,
    sla_to_dict,
)
from vnpost.schema import CourierCode, CourierSLA, ParcelStatus
from vnpost.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    at_hub,
    created,
    delivered,
    out_for_delivery,
    picked_up,
)


def _events_for_one_parcel() -> list:
    return [
        created("T-1", DEFAULT_TS),
        picked_up("T-1", DEFAULT_TS + timedelta(hours=2), hub="HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=8), "HN-CG"),
        out_for_delivery(
            "T-1",
            DEFAULT_TS + timedelta(hours=20),
            "HN-CG",
        ),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]


# ---------- ParcelEvent ------------------------------------------------------


def test_event_round_trip():
    e = picked_up("T-1", DEFAULT_TS, hub="HCM-TPN")
    assert event_from_dict(event_to_dict(e)) == e


def test_event_dump_load_many():
    events = _events_for_one_parcel()
    assert load_events(dump_events(events)) == events


def test_event_dump_newline_terminated():
    text = dump_events(_events_for_one_parcel())
    assert text.endswith("\n")


def test_event_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_events("[1, 2]\n")


def test_event_load_rejects_bool_as_str():
    bad = event_to_dict(picked_up("T-1", DEFAULT_TS))
    bad["hub_code"] = True
    with pytest.raises(TypeError, match="hub_code must be str"):
        event_from_dict(bad)


# ---------- Parcel -----------------------------------------------------------


def test_parcel_round_trip_delivered():
    parcels = stitch(_events_for_one_parcel())
    p = parcels[0]
    assert parcel_from_dict(parcel_to_dict(p)) == p


def test_parcel_round_trip_pending():
    parcels = stitch([created("T-1", DEFAULT_TS)])
    p = parcels[0]
    assert p.status is ParcelStatus.PENDING
    assert parcel_from_dict(parcel_to_dict(p)) == p


def test_parcel_dump_load():
    parcels = stitch(_events_for_one_parcel())
    assert load_parcels(dump_parcels(parcels)) == parcels


# ---------- CourierSLA -------------------------------------------------------


def test_sla_round_trip():
    s = CourierSLA(
        courier=CourierCode.GHN,
        n_parcels=100,
        n_delivered=95,
        n_on_time=85,
        median_transit_hours=48,
        p95_transit_hours=80,
        on_time_rate_pct=89.5,
    )
    assert sla_from_dict(sla_to_dict(s)) == s
    assert load_slas(dump_slas([s])) == [s]


# ---------- FraudFinding -----------------------------------------------------


def test_fraud_round_trip():
    f = FraudFinding(
        kind=FraudKind.SCAN_SKIPPING,
        courier=CourierCode.GHN,
        tracking_id="T-1",
        detail="only 3 scans",
        metric=3,
    )
    assert fraud_from_dict(fraud_to_dict(f)) == f
    assert load_frauds(dump_frauds([f])) == [f]
