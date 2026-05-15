"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from logietr.io_jsonl import (
    dump_events,
    dump_shipments,
    event_from_dict,
    load_events,
    load_shipments,
    shipment_from_dict,
)
from logietr.schema import ShipmentState

from ._fixtures import make_event, make_shipment


def test_shipment_roundtrip():
    s = make_shipment()
    text = dump_shipments([s])
    [back] = list(load_shipments(text))
    assert back == s


def test_event_roundtrip():
    ev = make_event(state=ShipmentState.DELIVERED, hub_code="HUB_01")
    text = dump_events([ev])
    [back] = list(load_events(text))
    assert back == ev


def test_event_with_null_hub_code():
    ev = make_event(hub_code=None)
    text = dump_events([ev])
    [back] = list(load_events(text))
    assert back.hub_code is None


def test_shipment_decoder_rejects_wrong_type():
    bad = {
        "shipment_id": 5,
        "order_id": "O",
        "carrier": "GHN",
        "origin_district": "A",
        "dest_district": "B",
        "weight_g": 100,
        "declared_value_vnd": 0,
        "promised_at": "2026-05-10T10:00:00+07:00",
        "created_at": "2026-05-10T09:00:00+07:00",
    }
    with pytest.raises(TypeError, match="shipment_id"):
        shipment_from_dict(bad)


def test_event_decoder_rejects_bool_for_int():
    """``bool`` is a subclass of ``int``; we must reject it explicitly."""
    bad = {
        "event_id": "E",
        "shipment_id": "S",
        "state": "PICKED_UP",
        "occurred_at": "2026-05-10T10:00:00+07:00",
        "hub_code": True,
    }
    with pytest.raises(TypeError, match="hub_code"):
        event_from_dict(bad)


def test_event_decoder_rejects_unknown_state():
    bad = {
        "event_id": "E",
        "shipment_id": "S",
        "state": "NOT_A_STATE",
        "occurred_at": "2026-05-10T10:00:00+07:00",
        "hub_code": None,
    }
    with pytest.raises(ValueError):
        event_from_dict(bad)


def test_shipment_decoder_rejects_unknown_carrier():
    bad = {
        "shipment_id": "S",
        "order_id": "O",
        "carrier": "DHL",
        "origin_district": "A",
        "dest_district": "B",
        "weight_g": 100,
        "declared_value_vnd": 0,
        "promised_at": "2026-05-10T10:00:00+07:00",
        "created_at": "2026-05-10T09:00:00+07:00",
    }
    with pytest.raises(ValueError):
        shipment_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_shipments([make_shipment()])
    blank_padded = "\n\n" + text + "\n\n"
    back = list(load_shipments(blank_padded))
    assert len(back) == 1


def test_multi_record_roundtrip():
    ships = [make_shipment(shipment_id=f"S-{i}", order_id=f"O-{i}") for i in range(5)]
    text = dump_shipments(ships)
    back = list(load_shipments(text))
    assert back == ships
