"""Type-checked JSONL codec for shipments + tracking events."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from logietr.schema import Carrier, Shipment, ShipmentState, TrackingEvent

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str | None, got {type(v).__name__}")
    return v


def shipment_to_dict(s: Shipment) -> dict[str, object]:
    return {
        "shipment_id": s.shipment_id,
        "order_id": s.order_id,
        "carrier": s.carrier.value,
        "origin_district": s.origin_district,
        "dest_district": s.dest_district,
        "weight_g": s.weight_g,
        "declared_value_vnd": s.declared_value_vnd,
        "promised_at": s.promised_at.isoformat(),
        "created_at": s.created_at.isoformat(),
    }


def shipment_from_dict(d: dict[str, object]) -> Shipment:
    return Shipment(
        shipment_id=_require_str(d, "shipment_id"),
        order_id=_require_str(d, "order_id"),
        carrier=Carrier(_require_str(d, "carrier")),
        origin_district=_require_str(d, "origin_district"),
        dest_district=_require_str(d, "dest_district"),
        weight_g=_require_int(d, "weight_g"),
        declared_value_vnd=_require_int(d, "declared_value_vnd"),
        promised_at=datetime.fromisoformat(_require_str(d, "promised_at")),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
    )


def event_to_dict(e: TrackingEvent) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "shipment_id": e.shipment_id,
        "state": e.state.value,
        "occurred_at": e.occurred_at.isoformat(),
        "hub_code": e.hub_code,
    }


def event_from_dict(d: dict[str, object]) -> TrackingEvent:
    return TrackingEvent(
        event_id=_require_str(d, "event_id"),
        shipment_id=_require_str(d, "shipment_id"),
        state=ShipmentState(_require_str(d, "state")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        hub_code=_optional_str(d, "hub_code"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_shipments(shipments: Iterable[Shipment]) -> str:
    return _dump(shipment_to_dict(s) for s in shipments)


def dump_events(events: Iterable[TrackingEvent]) -> str:
    return _dump(event_to_dict(e) for e in events)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_shipments(text: str) -> Iterator[Shipment]:
    for d in _iter_lines(text):
        yield shipment_from_dict(d)


def load_events(text: str) -> Iterator[TrackingEvent]:
    for d in _iter_lines(text):
        yield event_from_dict(d)


__all__ = [
    "dump_events",
    "dump_shipments",
    "event_from_dict",
    "event_to_dict",
    "load_events",
    "load_shipments",
    "shipment_from_dict",
    "shipment_to_dict",
]
