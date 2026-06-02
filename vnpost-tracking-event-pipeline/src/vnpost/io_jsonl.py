"""JSONL codec for ParcelEvent / Parcel / CourierSLA / FraudFinding."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vnpost.fraud import FraudFinding, FraudKind
from vnpost.schema import (
    CourierCode,
    CourierSLA,
    Parcel,
    ParcelEvent,
    ParcelEventKind,
    ParcelStatus,
)

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


def _require_number(d: dict[str, object], key: str) -> float:
    v = d[key]
    if not isinstance(v, int | float) or isinstance(v, bool):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


def _optional_dt(d: dict[str, object], key: str) -> datetime | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be ISO string | null, got {type(v).__name__}")
    return datetime.fromisoformat(v)


# ---------- ParcelEvent ------------------------------------------------------


def event_to_dict(e: ParcelEvent) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "tracking_id": e.tracking_id,
        "courier": e.courier.value,
        "kind": e.kind.value,
        "occurred_at": e.occurred_at.isoformat(),
        "hub_code": e.hub_code,
        "note": e.note,
    }


def event_from_dict(d: dict[str, object]) -> ParcelEvent:
    return ParcelEvent(
        event_id=_require_str(d, "event_id"),
        tracking_id=_require_str(d, "tracking_id"),
        courier=CourierCode(_require_str(d, "courier")),
        kind=ParcelEventKind(_require_str(d, "kind")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        hub_code=_require_str(d, "hub_code") if "hub_code" in d else "",
        note=_require_str(d, "note") if "note" in d else "",
    )


# ---------- Parcel -----------------------------------------------------------


def parcel_to_dict(p: Parcel) -> dict[str, object]:
    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt is not None else None

    return {
        "tracking_id": p.tracking_id,
        "courier": p.courier.value,
        "status": p.status.value,
        "created_at": p.created_at.isoformat(),
        "picked_up_at": _iso(p.picked_up_at),
        "delivered_at": _iso(p.delivered_at),
        "returned_at": _iso(p.returned_at),
        "last_event_at": p.last_event_at.isoformat(),
        "n_events": p.n_events,
        "n_hubs_visited": p.n_hubs_visited,
        "origin_hub": p.origin_hub,
        "dest_hub": p.dest_hub,
    }


def parcel_from_dict(d: dict[str, object]) -> Parcel:
    return Parcel(
        tracking_id=_require_str(d, "tracking_id"),
        courier=CourierCode(_require_str(d, "courier")),
        status=ParcelStatus(_require_str(d, "status")),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
        picked_up_at=_optional_dt(d, "picked_up_at"),
        delivered_at=_optional_dt(d, "delivered_at"),
        returned_at=_optional_dt(d, "returned_at"),
        last_event_at=datetime.fromisoformat(_require_str(d, "last_event_at")),
        n_events=_require_int(d, "n_events"),
        n_hubs_visited=_require_int(d, "n_hubs_visited"),
        origin_hub=_require_str(d, "origin_hub"),
        dest_hub=_require_str(d, "dest_hub"),
    )


# ---------- CourierSLA -------------------------------------------------------


def sla_to_dict(s: CourierSLA) -> dict[str, object]:
    return {
        "courier": s.courier.value,
        "n_parcels": s.n_parcels,
        "n_delivered": s.n_delivered,
        "n_on_time": s.n_on_time,
        "median_transit_hours": s.median_transit_hours,
        "p95_transit_hours": s.p95_transit_hours,
        "on_time_rate_pct": s.on_time_rate_pct,
    }


def sla_from_dict(d: dict[str, object]) -> CourierSLA:
    return CourierSLA(
        courier=CourierCode(_require_str(d, "courier")),
        n_parcels=_require_int(d, "n_parcels"),
        n_delivered=_require_int(d, "n_delivered"),
        n_on_time=_require_int(d, "n_on_time"),
        median_transit_hours=_require_int(d, "median_transit_hours"),
        p95_transit_hours=_require_int(d, "p95_transit_hours"),
        on_time_rate_pct=_require_number(d, "on_time_rate_pct"),
    )


# ---------- FraudFinding -----------------------------------------------------


def fraud_to_dict(f: FraudFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "courier": f.courier.value,
        "tracking_id": f.tracking_id,
        "detail": f.detail,
        "metric": f.metric,
    }


def fraud_from_dict(d: dict[str, object]) -> FraudFinding:
    return FraudFinding(
        kind=FraudKind(_require_str(d, "kind")),
        courier=CourierCode(_require_str(d, "courier")),
        tracking_id=_require_str(d, "tracking_id"),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- dump/load --------------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[ParcelEvent]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_parcels(items: Iterable[Parcel]) -> str:
    return _dump(parcel_to_dict(p) for p in items)


def dump_slas(items: Iterable[CourierSLA]) -> str:
    return _dump(sla_to_dict(s) for s in items)


def dump_frauds(items: Iterable[FraudFinding]) -> str:
    return _dump(fraud_to_dict(f) for f in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_events(text: str) -> list[ParcelEvent]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_parcels(text: str) -> list[Parcel]:
    return [parcel_from_dict(d) for d in _iter_lines(text)]


def load_slas(text: str) -> list[CourierSLA]:
    return [sla_from_dict(d) for d in _iter_lines(text)]


def load_frauds(text: str) -> list[FraudFinding]:
    return [fraud_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_events",
    "dump_frauds",
    "dump_parcels",
    "dump_slas",
    "event_from_dict",
    "event_to_dict",
    "fraud_from_dict",
    "fraud_to_dict",
    "load_events",
    "load_frauds",
    "load_parcels",
    "load_slas",
    "parcel_from_dict",
    "parcel_to_dict",
    "sla_from_dict",
    "sla_to_dict",
]
