"""JSONL codec for Trip / DriverSettlement / FraudFinding."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vnride.fraud import FraudFinding, FraudKind
from vnride.schema import (
    CancelledBy,
    DriverSettlement,
    FareBreakdown,
    PaymentMethod,
    ServiceType,
    Trip,
    TripState,
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


def _opt_str(d: dict[str, object], key: str) -> str:
    v = d.get(key, "")
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


# ---------- FareBreakdown ---------------------------------------------------


def fare_to_dict(f: FareBreakdown) -> dict[str, object]:
    return {
        "base_vnd": f.base_vnd,
        "distance_vnd": f.distance_vnd,
        "duration_vnd": f.duration_vnd,
        "booking_vnd": f.booking_vnd,
        "surge_multiplier_bps": f.surge_multiplier_bps,
    }


def fare_from_dict(d: dict[str, object]) -> FareBreakdown:
    return FareBreakdown(
        base_vnd=_require_int(d, "base_vnd"),
        distance_vnd=_require_int(d, "distance_vnd"),
        duration_vnd=_require_int(d, "duration_vnd"),
        booking_vnd=_require_int(d, "booking_vnd"),
        surge_multiplier_bps=_require_int(d, "surge_multiplier_bps"),
    )


# ---------- Trip ------------------------------------------------------------


def trip_to_dict(t: Trip) -> dict[str, object]:
    out: dict[str, object] = {
        "trip_id": t.trip_id,
        "operator": t.operator,
        "city": t.city,
        "service": t.service.value,
        "rider_id": t.rider_id,
        "driver_id": t.driver_id,
        "state": t.state.value,
        "requested_at": t.requested_at.isoformat(),
        "distance_cm": t.distance_cm,
        "duration_seconds": t.duration_seconds,
        "payment_method": t.payment_method.value,
    }
    if t.completed_at is not None:
        out["completed_at"] = t.completed_at.isoformat()
    if t.fare is not None:
        out["fare"] = fare_to_dict(t.fare)
    if t.cancelled_by is not None:
        out["cancelled_by"] = t.cancelled_by.value
    return out


def trip_from_dict(d: dict[str, object]) -> Trip:
    completed_at = None
    if "completed_at" in d:
        completed_at = datetime.fromisoformat(_require_str(d, "completed_at"))
    fare = None
    if "fare" in d:
        raw_fare = d["fare"]
        if not isinstance(raw_fare, dict):
            raise TypeError("fare must be dict")
        fare = fare_from_dict(raw_fare)
    cancelled_by = None
    if "cancelled_by" in d:
        cancelled_by = CancelledBy(_require_str(d, "cancelled_by"))
    return Trip(
        trip_id=_require_str(d, "trip_id"),
        operator=_require_str(d, "operator"),
        city=_require_str(d, "city"),
        service=ServiceType(_require_str(d, "service")),
        rider_id=_require_str(d, "rider_id"),
        driver_id=_opt_str(d, "driver_id"),
        state=TripState(_require_str(d, "state")),
        requested_at=datetime.fromisoformat(_require_str(d, "requested_at")),
        completed_at=completed_at,
        distance_cm=_require_int(d, "distance_cm") if "distance_cm" in d else 0,
        duration_seconds=(_require_int(d, "duration_seconds") if "duration_seconds" in d else 0),
        fare=fare,
        payment_method=PaymentMethod(
            _opt_str(d, "payment_method") or PaymentMethod.CASH.value,
        ),
        cancelled_by=cancelled_by,
    )


# ---------- DriverSettlement ------------------------------------------------


def settlement_to_dict(s: DriverSettlement) -> dict[str, object]:
    return {
        "driver_id": s.driver_id,
        "operator": s.operator,
        "date": s.date,
        "n_completed_trips": s.n_completed_trips,
        "n_cancelled_trips": s.n_cancelled_trips,
        "gross_revenue_vnd": s.gross_revenue_vnd,
        "commission_vnd": s.commission_vnd,
        "cash_collected_vnd": s.cash_collected_vnd,
        "net_payable_vnd": s.net_payable_vnd,
    }


def settlement_from_dict(d: dict[str, object]) -> DriverSettlement:
    return DriverSettlement(
        driver_id=_require_str(d, "driver_id"),
        operator=_require_str(d, "operator"),
        date=_require_str(d, "date"),
        n_completed_trips=_require_int(d, "n_completed_trips"),
        n_cancelled_trips=_require_int(d, "n_cancelled_trips"),
        gross_revenue_vnd=_require_int(d, "gross_revenue_vnd"),
        commission_vnd=_require_int(d, "commission_vnd"),
        cash_collected_vnd=_require_int(d, "cash_collected_vnd"),
        net_payable_vnd=_require_int(d, "net_payable_vnd"),
    )


# ---------- FraudFinding ----------------------------------------------------


def fraud_to_dict(f: FraudFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "subject_id": f.subject_id,
        "operator": f.operator,
        "detail": f.detail,
        "metric": f.metric,
    }


def fraud_from_dict(d: dict[str, object]) -> FraudFinding:
    return FraudFinding(
        kind=FraudKind(_require_str(d, "kind")),
        subject_id=_require_str(d, "subject_id"),
        operator=_require_str(d, "operator"),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_trips(items: Iterable[Trip]) -> str:
    return _dump(trip_to_dict(t) for t in items)


def dump_settlements(items: Iterable[DriverSettlement]) -> str:
    return _dump(settlement_to_dict(s) for s in items)


def dump_frauds(items: Iterable[FraudFinding]) -> str:
    return _dump(fraud_to_dict(f) for f in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_trips(text: str) -> list[Trip]:
    return [trip_from_dict(d) for d in _iter_lines(text)]


def load_settlements(text: str) -> list[DriverSettlement]:
    return [settlement_from_dict(d) for d in _iter_lines(text)]


def load_frauds(text: str) -> list[FraudFinding]:
    return [fraud_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_frauds",
    "dump_settlements",
    "dump_trips",
    "fare_from_dict",
    "fare_to_dict",
    "fraud_from_dict",
    "fraud_to_dict",
    "load_frauds",
    "load_settlements",
    "load_trips",
    "settlement_from_dict",
    "settlement_to_dict",
    "trip_from_dict",
    "trip_to_dict",
]
