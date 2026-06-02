"""Type-checked JSONL codec for events, attributions, cohorts, fraud findings."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from mappev.fraud import FraudFinding, FraudKind
from mappev.schema import (
    Attribution,
    CohortLTV,
    CohortRetention,
    Event,
    EventKind,
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


def event_to_dict(e: Event) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "device_id": e.device_id,
        "kind": e.kind.value,
        "occurred_at": e.occurred_at.isoformat(),
        "source": e.source,
        "campaign": e.campaign,
        "revenue_vnd": e.revenue_vnd,
        "in_app_event_name": e.in_app_event_name,
    }


def event_from_dict(d: dict[str, object]) -> Event:
    return Event(
        event_id=_require_str(d, "event_id"),
        device_id=_require_str(d, "device_id"),
        kind=EventKind(_require_str(d, "kind")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        source=_require_str(d, "source"),
        campaign=_require_str(d, "campaign"),
        revenue_vnd=_require_int(d, "revenue_vnd") if "revenue_vnd" in d else 0,
        in_app_event_name=_require_str(d, "in_app_event_name") if "in_app_event_name" in d else "",
    )


def attribution_to_dict(a: Attribution) -> dict[str, object]:
    return {
        "device_id": a.device_id,
        "install_at": a.install_at.isoformat(),
        "attributed_source": a.attributed_source,
        "attributed_campaign": a.attributed_campaign,
        "attribution_event_id": a.attribution_event_id,
        "attribution_lag_seconds": a.attribution_lag_seconds,
    }


def attribution_from_dict(d: dict[str, object]) -> Attribution:
    return Attribution(
        device_id=_require_str(d, "device_id"),
        install_at=datetime.fromisoformat(_require_str(d, "install_at")),
        attributed_source=_require_str(d, "attributed_source"),
        attributed_campaign=_require_str(d, "attributed_campaign"),
        attribution_event_id=_optional_str(d, "attribution_event_id"),
        attribution_lag_seconds=_require_int(d, "attribution_lag_seconds"),
    )


def retention_to_dict(r: CohortRetention) -> dict[str, object]:
    return {
        "cohort_date": r.cohort_date,
        "cohort_size": r.cohort_size,
        "d1_active": r.d1_active,
        "d7_active": r.d7_active,
        "d30_active": r.d30_active,
    }


def retention_from_dict(d: dict[str, object]) -> CohortRetention:
    return CohortRetention(
        cohort_date=_require_str(d, "cohort_date"),
        cohort_size=_require_int(d, "cohort_size"),
        d1_active=_require_int(d, "d1_active"),
        d7_active=_require_int(d, "d7_active"),
        d30_active=_require_int(d, "d30_active"),
    )


def ltv_to_dict(c: CohortLTV) -> dict[str, object]:
    return {
        "cohort_date": c.cohort_date,
        "cohort_size": c.cohort_size,
        "revenue_d1_vnd": c.revenue_d1_vnd,
        "revenue_d7_vnd": c.revenue_d7_vnd,
        "revenue_d30_vnd": c.revenue_d30_vnd,
    }


def ltv_from_dict(d: dict[str, object]) -> CohortLTV:
    return CohortLTV(
        cohort_date=_require_str(d, "cohort_date"),
        cohort_size=_require_int(d, "cohort_size"),
        revenue_d1_vnd=_require_int(d, "revenue_d1_vnd"),
        revenue_d7_vnd=_require_int(d, "revenue_d7_vnd"),
        revenue_d30_vnd=_require_int(d, "revenue_d30_vnd"),
    )


def fraud_to_dict(f: FraudFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "source": f.source,
        "detail": f.detail,
        "metric": f.metric,
        "devices_affected": f.devices_affected,
    }


def fraud_from_dict(d: dict[str, object]) -> FraudFinding:
    return FraudFinding(
        kind=FraudKind(_require_str(d, "kind")),
        source=_require_str(d, "source"),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
        devices_affected=_require_int(d, "devices_affected"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[Event]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_attributions(items: Iterable[Attribution]) -> str:
    return _dump(attribution_to_dict(a) for a in items)


def dump_retentions(items: Iterable[CohortRetention]) -> str:
    return _dump(retention_to_dict(r) for r in items)


def dump_ltvs(items: Iterable[CohortLTV]) -> str:
    return _dump(ltv_to_dict(c) for c in items)


def dump_frauds(items: Iterable[FraudFinding]) -> str:
    return _dump(fraud_to_dict(f) for f in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_events(text: str) -> list[Event]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_attributions(text: str) -> list[Attribution]:
    return [attribution_from_dict(d) for d in _iter_lines(text)]


def load_retentions(text: str) -> list[CohortRetention]:
    return [retention_from_dict(d) for d in _iter_lines(text)]


def load_ltvs(text: str) -> list[CohortLTV]:
    return [ltv_from_dict(d) for d in _iter_lines(text)]


def load_frauds(text: str) -> list[FraudFinding]:
    return [fraud_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "attribution_from_dict",
    "attribution_to_dict",
    "dump_attributions",
    "dump_events",
    "dump_frauds",
    "dump_ltvs",
    "dump_retentions",
    "event_from_dict",
    "event_to_dict",
    "fraud_from_dict",
    "fraud_to_dict",
    "load_attributions",
    "load_events",
    "load_frauds",
    "load_ltvs",
    "load_retentions",
    "ltv_from_dict",
    "ltv_to_dict",
    "retention_from_dict",
    "retention_to_dict",
]
