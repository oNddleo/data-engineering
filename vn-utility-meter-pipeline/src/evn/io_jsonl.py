"""JSONL codec for MeterReading / ElectricityBill / AnnualSummary / AnomalyFinding."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from evn.aggregator import AnnualSummary
from evn.schema import (
    AnomalyFinding,
    AnomalyKind,
    CustomerCategory,
    ElectricityBill,
    MeterReading,
    TierUsage,
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


def _require_list(d: dict[str, object], key: str) -> list[object]:
    v = d[key]
    if not isinstance(v, list):
        raise TypeError(f"{key} must be list, got {type(v).__name__}")
    return v


# ---------- MeterReading ---------------------------------------------------


def reading_to_dict(r: MeterReading) -> dict[str, object]:
    return {
        "customer_code": r.customer_code,
        "category": r.category.value,
        "period_start": r.period_start.isoformat(),
        "period_end": r.period_end.isoformat(),
        "kwh_used": r.kwh_used,
    }


def reading_from_dict(d: dict[str, object]) -> MeterReading:
    return MeterReading(
        customer_code=_require_str(d, "customer_code"),
        category=CustomerCategory(_require_str(d, "category")),
        period_start=date.fromisoformat(_require_str(d, "period_start")),
        period_end=date.fromisoformat(_require_str(d, "period_end")),
        kwh_used=_require_int(d, "kwh_used"),
    )


# ---------- TierUsage + ElectricityBill ------------------------------------


def _tier_to_dict(t: TierUsage) -> dict[str, object]:
    return {
        "tier_index": t.tier_index,
        "kwh": t.kwh,
        "rate_vnd_per_kwh": t.rate_vnd_per_kwh,
        "amount_vnd": t.amount_vnd,
    }


def _tier_from_dict(d: dict[str, object]) -> TierUsage:
    return TierUsage(
        tier_index=_require_int(d, "tier_index"),
        kwh=_require_int(d, "kwh"),
        rate_vnd_per_kwh=_require_int(d, "rate_vnd_per_kwh"),
        amount_vnd=_require_int(d, "amount_vnd"),
    )


def bill_to_dict(b: ElectricityBill) -> dict[str, object]:
    return {
        "customer_code": b.customer_code,
        "category": b.category.value,
        "period_start": b.period_start.isoformat(),
        "period_end": b.period_end.isoformat(),
        "kwh_used": b.kwh_used,
        "pre_vat_amount_vnd": b.pre_vat_amount_vnd,
        "vat_amount_vnd": b.vat_amount_vnd,
        "tier_breakdown": [_tier_to_dict(t) for t in b.tier_breakdown],
    }


def bill_from_dict(d: dict[str, object]) -> ElectricityBill:
    raw_tiers = _require_list(d, "tier_breakdown") if "tier_breakdown" in d else []
    tiers: list[TierUsage] = []
    for entry in raw_tiers:
        if not isinstance(entry, dict):
            raise TypeError("tier_breakdown entry must be dict")
        tiers.append(_tier_from_dict(entry))
    return ElectricityBill(
        customer_code=_require_str(d, "customer_code"),
        category=CustomerCategory(_require_str(d, "category")),
        period_start=date.fromisoformat(_require_str(d, "period_start")),
        period_end=date.fromisoformat(_require_str(d, "period_end")),
        kwh_used=_require_int(d, "kwh_used"),
        pre_vat_amount_vnd=_require_int(d, "pre_vat_amount_vnd"),
        vat_amount_vnd=_require_int(d, "vat_amount_vnd"),
        tier_breakdown=tuple(tiers),
    )


# ---------- AnnualSummary --------------------------------------------------


def summary_to_dict(s: AnnualSummary) -> dict[str, object]:
    return {
        "customer_code": s.customer_code,
        "category": s.category.value,
        "n_bills": s.n_bills,
        "total_kwh": s.total_kwh,
        "total_pre_vat_vnd": s.total_pre_vat_vnd,
        "total_vat_vnd": s.total_vat_vnd,
    }


def summary_from_dict(d: dict[str, object]) -> AnnualSummary:
    return AnnualSummary(
        customer_code=_require_str(d, "customer_code"),
        category=CustomerCategory(_require_str(d, "category")),
        n_bills=_require_int(d, "n_bills"),
        total_kwh=_require_int(d, "total_kwh"),
        total_pre_vat_vnd=_require_int(d, "total_pre_vat_vnd"),
        total_vat_vnd=_require_int(d, "total_vat_vnd"),
    )


# ---------- AnomalyFinding -------------------------------------------------


def anomaly_to_dict(f: AnomalyFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "customer_code": f.customer_code,
        "category": f.category.value,
        "detail": f.detail,
        "metric": f.metric,
    }


def anomaly_from_dict(d: dict[str, object]) -> AnomalyFinding:
    return AnomalyFinding(
        kind=AnomalyKind(_require_str(d, "kind")),
        customer_code=_require_str(d, "customer_code"),
        category=CustomerCategory(_require_str(d, "category")),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_readings(items: Iterable[MeterReading]) -> str:
    return _dump(reading_to_dict(r) for r in items)


def dump_bills(items: Iterable[ElectricityBill]) -> str:
    return _dump(bill_to_dict(b) for b in items)


def dump_summaries(items: Iterable[AnnualSummary]) -> str:
    return _dump(summary_to_dict(s) for s in items)


def dump_anomalies(items: Iterable[AnomalyFinding]) -> str:
    return _dump(anomaly_to_dict(f) for f in items)


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


def load_readings(text: str) -> list[MeterReading]:
    return [reading_from_dict(d) for d in _iter_lines(text)]


def load_bills(text: str) -> list[ElectricityBill]:
    return [bill_from_dict(d) for d in _iter_lines(text)]


def load_summaries(text: str) -> list[AnnualSummary]:
    return [summary_from_dict(d) for d in _iter_lines(text)]


def load_anomalies(text: str) -> list[AnomalyFinding]:
    return [anomaly_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "anomaly_from_dict",
    "anomaly_to_dict",
    "bill_from_dict",
    "bill_to_dict",
    "dump_anomalies",
    "dump_bills",
    "dump_readings",
    "dump_summaries",
    "load_anomalies",
    "load_bills",
    "load_readings",
    "load_summaries",
    "reading_from_dict",
    "reading_to_dict",
    "summary_from_dict",
    "summary_to_dict",
]
