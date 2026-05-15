"""JSONL codec for Event + WindowAggregate + HotnessEvent."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from flashpipe.detectors import HotnessEvent, HotnessKind
from flashpipe.events import Event, EventKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from flashpipe.windows import WindowAggregate


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


def event_to_dict(e: Event) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "kind": e.kind.value,
        "user_id": e.user_id,
        "item_id": e.item_id,
        "shop_id": e.shop_id,
        "quantity": e.quantity,
        "amount_vnd": e.amount_vnd,
        "created_at": e.created_at.isoformat(),
    }


def event_from_dict(d: dict[str, object]) -> Event:
    return Event(
        event_id=_require_str(d, "event_id"),
        kind=EventKind(_require_str(d, "kind")),
        user_id=_require_str(d, "user_id"),
        item_id=_require_int(d, "item_id"),
        shop_id=_require_int(d, "shop_id"),
        quantity=_require_int(d, "quantity"),
        amount_vnd=_require_int(d, "amount_vnd"),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
    )


def aggregate_to_dict(a: WindowAggregate) -> dict[str, object]:
    return {
        "window_start": a.window_start.isoformat(),
        "window_end": a.window_end.isoformat(),
        "item_id": a.item_id,
        "n_views": a.n_views,
        "n_add_to_cart": a.n_add_to_cart,
        "n_checkout": a.n_checkout,
        "n_orders": a.n_orders,
        "units_sold": a.units_sold,
        "gmv_vnd": a.gmv_vnd,
        "unique_users": a.unique_users,
    }


def hotness_to_dict(h: HotnessEvent) -> dict[str, object]:
    return {
        "kind": h.kind.value,
        "item_id": h.item_id,
        "window_start": h.window_start.isoformat(),
        "window_end": h.window_end.isoformat(),
        "detail": h.detail,
        "metric": h.metric,
    }


def hotness_from_dict(d: dict[str, object]) -> HotnessEvent:
    return HotnessEvent(
        kind=HotnessKind(_require_str(d, "kind")),
        item_id=_require_int(d, "item_id"),
        window_start=datetime.fromisoformat(_require_str(d, "window_start")),
        window_end=datetime.fromisoformat(_require_str(d, "window_end")),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


def dump_events(events: Iterable[Event]) -> str:
    return "\n".join(json.dumps(event_to_dict(e), ensure_ascii=False) for e in events) + "\n"


def load_events(text: str) -> Iterator[Event]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield event_from_dict(json.loads(line))


def dump_aggregates(aggs: Iterable[WindowAggregate]) -> str:
    return "\n".join(json.dumps(aggregate_to_dict(a), ensure_ascii=False) for a in aggs) + "\n"


def dump_hotness(events: Iterable[HotnessEvent]) -> str:
    return "\n".join(json.dumps(hotness_to_dict(h), ensure_ascii=False) for h in events) + "\n"


__all__ = [
    "aggregate_to_dict",
    "dump_aggregates",
    "dump_events",
    "dump_hotness",
    "event_from_dict",
    "event_to_dict",
    "hotness_from_dict",
    "hotness_to_dict",
    "load_events",
]
