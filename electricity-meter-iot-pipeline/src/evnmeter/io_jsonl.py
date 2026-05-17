"""Type-checked JSONL codec for meters, readings, intervals, bills."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from evnmeter.billing import MonthlyBill
from evnmeter.schema import ConsumptionInterval, Meter, MeterKind, Reading
from evnmeter.tariff import TierBreakdown

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


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def meter_to_dict(m: Meter) -> dict[str, object]:
    return {
        "meter_id": m.meter_id,
        "customer_id": m.customer_id,
        "kind": m.kind.value,
        "region_code": m.region_code,
        "installed_at": m.installed_at.isoformat(),
    }


def meter_from_dict(d: dict[str, object]) -> Meter:
    return Meter(
        meter_id=_require_str(d, "meter_id"),
        customer_id=_require_str(d, "customer_id"),
        kind=MeterKind(_require_str(d, "kind")),
        region_code=_require_str(d, "region_code"),
        installed_at=datetime.fromisoformat(_require_str(d, "installed_at")),
    )


def reading_to_dict(r: Reading) -> dict[str, object]:
    return {
        "meter_id": r.meter_id,
        "cumulative_kwh_x100": r.cumulative_kwh_x100,
        "observed_at": r.observed_at.isoformat(),
        "quality": r.quality,
    }


def reading_from_dict(d: dict[str, object]) -> Reading:
    return Reading(
        meter_id=_require_str(d, "meter_id"),
        cumulative_kwh_x100=_require_int(d, "cumulative_kwh_x100"),
        observed_at=datetime.fromisoformat(_require_str(d, "observed_at")),
        quality=_require_str(d, "quality"),
    )


def interval_to_dict(c: ConsumptionInterval) -> dict[str, object]:
    return {
        "meter_id": c.meter_id,
        "start_at": c.start_at.isoformat(),
        "end_at": c.end_at.isoformat(),
        "kwh_x100": c.kwh_x100,
        "is_estimated": c.is_estimated,
    }


def interval_from_dict(d: dict[str, object]) -> ConsumptionInterval:
    return ConsumptionInterval(
        meter_id=_require_str(d, "meter_id"),
        start_at=datetime.fromisoformat(_require_str(d, "start_at")),
        end_at=datetime.fromisoformat(_require_str(d, "end_at")),
        kwh_x100=_require_int(d, "kwh_x100"),
        is_estimated=_require_bool(d, "is_estimated"),
    )


def bill_to_dict(b: MonthlyBill) -> dict[str, object]:
    return {
        "meter_id": b.meter_id,
        "period_start": b.period_start.isoformat(),
        "period_end": b.period_end.isoformat(),
        "billed_kwh": b.billed_kwh,
        "breakdown": [
            {"tier": br.tier, "kwh": br.kwh, "rate_vnd_per_kwh": br.rate_vnd_per_kwh, "vnd": br.vnd}
            for br in b.breakdown
        ],
        "subtotal_vnd": b.subtotal_vnd,
        "vat_vnd": b.vat_vnd,
        "grand_total_vnd": b.grand_total_vnd,
        "n_estimated_intervals": b.n_estimated_intervals,
    }


def bill_from_dict(d: dict[str, object]) -> MonthlyBill:
    raw_breakdown = d["breakdown"]
    if not isinstance(raw_breakdown, list):
        raise TypeError("breakdown must be a list")
    breakdown = tuple(
        TierBreakdown(
            tier=_require_int(br, "tier"),
            kwh=_require_int(br, "kwh"),
            rate_vnd_per_kwh=_require_int(br, "rate_vnd_per_kwh"),
            vnd=_require_int(br, "vnd"),
        )
        for br in raw_breakdown
        if isinstance(br, dict)
    )
    return MonthlyBill(
        meter_id=_require_str(d, "meter_id"),
        period_start=datetime.fromisoformat(_require_str(d, "period_start")),
        period_end=datetime.fromisoformat(_require_str(d, "period_end")),
        billed_kwh=_require_int(d, "billed_kwh"),
        breakdown=breakdown,
        subtotal_vnd=_require_int(d, "subtotal_vnd"),
        vat_vnd=_require_int(d, "vat_vnd"),
        grand_total_vnd=_require_int(d, "grand_total_vnd"),
        n_estimated_intervals=_require_int(d, "n_estimated_intervals"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_meters(meters: Iterable[Meter]) -> str:
    return _dump(meter_to_dict(m) for m in meters)


def dump_readings(readings: Iterable[Reading]) -> str:
    return _dump(reading_to_dict(r) for r in readings)


def dump_intervals(intervals: Iterable[ConsumptionInterval]) -> str:
    return _dump(interval_to_dict(c) for c in intervals)


def dump_bills(bills: Iterable[MonthlyBill]) -> str:
    return _dump(bill_to_dict(b) for b in bills)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_meters(text: str) -> Iterator[Meter]:
    for d in _iter_lines(text):
        yield meter_from_dict(d)


def load_readings(text: str) -> Iterator[Reading]:
    for d in _iter_lines(text):
        yield reading_from_dict(d)


def load_intervals(text: str) -> Iterator[ConsumptionInterval]:
    for d in _iter_lines(text):
        yield interval_from_dict(d)


def load_bills(text: str) -> Iterator[MonthlyBill]:
    for d in _iter_lines(text):
        yield bill_from_dict(d)


__all__ = [
    "bill_from_dict",
    "bill_to_dict",
    "dump_bills",
    "dump_intervals",
    "dump_meters",
    "dump_readings",
    "interval_from_dict",
    "interval_to_dict",
    "load_bills",
    "load_intervals",
    "load_meters",
    "load_readings",
    "meter_from_dict",
    "meter_to_dict",
    "reading_from_dict",
    "reading_to_dict",
]
