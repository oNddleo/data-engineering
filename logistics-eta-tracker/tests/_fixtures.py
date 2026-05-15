"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from logietr.schema import VN_TZ, Carrier, Shipment, ShipmentState, TrackingEvent

DEFAULT_TS = datetime(2026, 5, 10, 9, 0, 0, tzinfo=VN_TZ)


def make_shipment(**overrides: Any) -> Shipment:
    defaults = {
        "shipment_id": "S-0001",
        "order_id": "O-0001",
        "carrier": Carrier.GHN,
        "origin_district": "HCMC_District1",
        "dest_district": "HN_HoanKiem",
        "weight_g": 500,
        "declared_value_vnd": 199_000,
        "promised_at": DEFAULT_TS + timedelta(hours=36),
        "created_at": DEFAULT_TS,
    }
    defaults.update(overrides)
    return Shipment(**defaults)  # type: ignore[arg-type]


def make_event(**overrides: Any) -> TrackingEvent:
    defaults = {
        "event_id": "E-0001",
        "shipment_id": "S-0001",
        "state": ShipmentState.PICKED_UP,
        "occurred_at": DEFAULT_TS + timedelta(hours=1),
        "hub_code": None,
    }
    defaults.update(overrides)
    return TrackingEvent(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_event", "make_shipment"]
