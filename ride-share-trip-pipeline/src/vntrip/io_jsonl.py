"""Type-checked JSONL codec for trip events, trips, fares, surges,
shifts, fraud findings."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vntrip.fraud import FraudFinding, FraudKind
from vntrip.schema import (
    CancelBy,
    DriverShift,
    FareBreakdown,
    SurgeWindow,
    Trip,
    TripEvent,
    TripEventKind,
    VehicleClass,
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


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str | null, got {type(v).__name__}")
    return v


def _optional_datetime(d: dict[str, object], key: str) -> datetime | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be ISO string | null, got {type(v).__name__}")
    return datetime.fromisoformat(v)


# ---------- TripEvent --------------------------------------------------------


def event_to_dict(e: TripEvent) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "trip_id": e.trip_id,
        "rider_id": e.rider_id,
        "driver_id": e.driver_id,
        "kind": e.kind.value,
        "occurred_at": e.occurred_at.isoformat(),
        "district": e.district,
        "lat_x10000": e.lat_x10000,
        "lon_x10000": e.lon_x10000,
        "vehicle_class": e.vehicle_class.value,
        "distance_m": e.distance_m,
        "fare_vnd": e.fare_vnd,
        "surge_bps": e.surge_bps,
        "cancel_by": e.cancel_by.value if e.cancel_by is not None else None,
    }


def event_from_dict(d: dict[str, object]) -> TripEvent:
    cancel_by_raw = _optional_str(d, "cancel_by")
    return TripEvent(
        event_id=_require_str(d, "event_id"),
        trip_id=_require_str(d, "trip_id"),
        rider_id=_require_str(d, "rider_id"),
        driver_id=_require_str(d, "driver_id"),
        kind=TripEventKind(_require_str(d, "kind")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        district=_require_str(d, "district"),
        lat_x10000=_require_int(d, "lat_x10000") if "lat_x10000" in d else 0,
        lon_x10000=_require_int(d, "lon_x10000") if "lon_x10000" in d else 0,
        vehicle_class=VehicleClass(_require_str(d, "vehicle_class")),
        distance_m=_require_int(d, "distance_m") if "distance_m" in d else 0,
        fare_vnd=_require_int(d, "fare_vnd") if "fare_vnd" in d else 0,
        surge_bps=_require_int(d, "surge_bps") if "surge_bps" in d else 10_000,
        cancel_by=CancelBy(cancel_by_raw) if cancel_by_raw is not None else None,
    )


# ---------- Trip -------------------------------------------------------------


def trip_to_dict(t: Trip) -> dict[str, object]:
    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt is not None else None

    return {
        "trip_id": t.trip_id,
        "rider_id": t.rider_id,
        "driver_id": t.driver_id,
        "vehicle_class": t.vehicle_class.value,
        "origin_district": t.origin_district,
        "dest_district": t.dest_district,
        "requested_at": t.requested_at.isoformat(),
        "accepted_at": _iso(t.accepted_at),
        "picked_up_at": _iso(t.picked_up_at),
        "dropped_off_at": _iso(t.dropped_off_at),
        "cancelled_at": _iso(t.cancelled_at),
        "cancel_by": t.cancel_by.value if t.cancel_by is not None else None,
        "distance_m": t.distance_m,
        "fare_vnd": t.fare_vnd,
        "surge_bps": t.surge_bps,
    }


def trip_from_dict(d: dict[str, object]) -> Trip:
    cancel_by_raw = _optional_str(d, "cancel_by")
    return Trip(
        trip_id=_require_str(d, "trip_id"),
        rider_id=_require_str(d, "rider_id"),
        driver_id=_require_str(d, "driver_id"),
        vehicle_class=VehicleClass(_require_str(d, "vehicle_class")),
        origin_district=_require_str(d, "origin_district"),
        dest_district=_require_str(d, "dest_district"),
        requested_at=datetime.fromisoformat(_require_str(d, "requested_at")),
        accepted_at=_optional_datetime(d, "accepted_at"),
        picked_up_at=_optional_datetime(d, "picked_up_at"),
        dropped_off_at=_optional_datetime(d, "dropped_off_at"),
        cancelled_at=_optional_datetime(d, "cancelled_at"),
        cancel_by=CancelBy(cancel_by_raw) if cancel_by_raw is not None else None,
        distance_m=_require_int(d, "distance_m"),
        fare_vnd=_require_int(d, "fare_vnd"),
        surge_bps=_require_int(d, "surge_bps"),
    )


# ---------- FareBreakdown ----------------------------------------------------


def fare_to_dict(f: FareBreakdown) -> dict[str, object]:
    return {
        "trip_id": f.trip_id,
        "base_fare_vnd": f.base_fare_vnd,
        "distance_fare_vnd": f.distance_fare_vnd,
        "time_fare_vnd": f.time_fare_vnd,
        "surge_multiplier_bps": f.surge_multiplier_bps,
        "pre_surge_subtotal_vnd": f.pre_surge_subtotal_vnd,
        "total_fare_vnd": f.total_fare_vnd,
    }


def fare_from_dict(d: dict[str, object]) -> FareBreakdown:
    return FareBreakdown(
        trip_id=_require_str(d, "trip_id"),
        base_fare_vnd=_require_int(d, "base_fare_vnd"),
        distance_fare_vnd=_require_int(d, "distance_fare_vnd"),
        time_fare_vnd=_require_int(d, "time_fare_vnd"),
        surge_multiplier_bps=_require_int(d, "surge_multiplier_bps"),
        pre_surge_subtotal_vnd=_require_int(d, "pre_surge_subtotal_vnd"),
        total_fare_vnd=_require_int(d, "total_fare_vnd"),
    )


# ---------- SurgeWindow ------------------------------------------------------


def surge_to_dict(w: SurgeWindow) -> dict[str, object]:
    return {
        "district": w.district,
        "hour_bucket": w.hour_bucket,
        "requests": w.requests,
        "completed_trips": w.completed_trips,
        "completion_rate_pct": w.completion_rate_pct,
        "avg_surge_bps": w.avg_surge_bps,
    }


def surge_from_dict(d: dict[str, object]) -> SurgeWindow:
    rate = d["completion_rate_pct"]
    if not isinstance(rate, int | float) or isinstance(rate, bool):
        raise TypeError("completion_rate_pct must be number")
    return SurgeWindow(
        district=_require_str(d, "district"),
        hour_bucket=_require_str(d, "hour_bucket"),
        requests=_require_int(d, "requests"),
        completed_trips=_require_int(d, "completed_trips"),
        completion_rate_pct=float(rate),
        avg_surge_bps=_require_int(d, "avg_surge_bps"),
    )


# ---------- DriverShift ------------------------------------------------------


def shift_to_dict(s: DriverShift) -> dict[str, object]:
    return {
        "driver_id": s.driver_id,
        "shift_date": s.shift_date,
        "trips_completed": s.trips_completed,
        "trips_cancelled_by_driver": s.trips_cancelled_by_driver,
        "online_seconds": s.online_seconds,
        "on_trip_seconds": s.on_trip_seconds,
        "revenue_vnd": s.revenue_vnd,
    }


def shift_from_dict(d: dict[str, object]) -> DriverShift:
    return DriverShift(
        driver_id=_require_str(d, "driver_id"),
        shift_date=_require_str(d, "shift_date"),
        trips_completed=_require_int(d, "trips_completed"),
        trips_cancelled_by_driver=_require_int(d, "trips_cancelled_by_driver"),
        online_seconds=_require_int(d, "online_seconds"),
        on_trip_seconds=_require_int(d, "on_trip_seconds"),
        revenue_vnd=_require_int(d, "revenue_vnd"),
    )


# ---------- FraudFinding -----------------------------------------------------


def fraud_to_dict(f: FraudFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "subject_id": f.subject_id,
        "detail": f.detail,
        "metric": f.metric,
        "trips_affected": f.trips_affected,
    }


def fraud_from_dict(d: dict[str, object]) -> FraudFinding:
    return FraudFinding(
        kind=FraudKind(_require_str(d, "kind")),
        subject_id=_require_str(d, "subject_id"),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
        trips_affected=_require_int(d, "trips_affected"),
    )


# ---------- dump/load --------------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[TripEvent]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_trips(items: Iterable[Trip]) -> str:
    return _dump(trip_to_dict(t) for t in items)


def dump_fares(items: Iterable[FareBreakdown]) -> str:
    return _dump(fare_to_dict(f) for f in items)


def dump_surges(items: Iterable[SurgeWindow]) -> str:
    return _dump(surge_to_dict(w) for w in items)


def dump_shifts(items: Iterable[DriverShift]) -> str:
    return _dump(shift_to_dict(s) for s in items)


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


def load_events(text: str) -> list[TripEvent]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_trips(text: str) -> list[Trip]:
    return [trip_from_dict(d) for d in _iter_lines(text)]


def load_fares(text: str) -> list[FareBreakdown]:
    return [fare_from_dict(d) for d in _iter_lines(text)]


def load_surges(text: str) -> list[SurgeWindow]:
    return [surge_from_dict(d) for d in _iter_lines(text)]


def load_shifts(text: str) -> list[DriverShift]:
    return [shift_from_dict(d) for d in _iter_lines(text)]


def load_frauds(text: str) -> list[FraudFinding]:
    return [fraud_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_events",
    "dump_fares",
    "dump_frauds",
    "dump_shifts",
    "dump_surges",
    "dump_trips",
    "event_from_dict",
    "event_to_dict",
    "fare_from_dict",
    "fare_to_dict",
    "fraud_from_dict",
    "fraud_to_dict",
    "load_events",
    "load_fares",
    "load_frauds",
    "load_shifts",
    "load_surges",
    "load_trips",
    "shift_from_dict",
    "shift_to_dict",
    "surge_from_dict",
    "surge_to_dict",
    "trip_from_dict",
    "trip_to_dict",
]
