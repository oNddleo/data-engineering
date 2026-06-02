"""Type-checked JSONL codec."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from cartrec.attribute import AttributedTouch, AttributionVerdict
from cartrec.schema import CampaignTouch, Event, EventKind, Session, TouchChannel

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


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def _optional_int(d: dict[str, object], key: str) -> int | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int or null, got {type(v).__name__}")
    return v


def event_to_dict(e: Event) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "buyer_id": e.buyer_id,
        "kind": e.kind.value,
        "occurred_at": e.occurred_at.isoformat(),
        "item_id": e.item_id,
        "unit_price_vnd": e.unit_price_vnd,
    }


def event_from_dict(d: dict[str, object]) -> Event:
    return Event(
        event_id=_require_str(d, "event_id"),
        buyer_id=_require_str(d, "buyer_id"),
        kind=EventKind(_require_str(d, "kind")),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        item_id=_optional_str(d, "item_id"),
        unit_price_vnd=_optional_int(d, "unit_price_vnd"),
    )


def session_to_dict(s: Session) -> dict[str, object]:
    return {
        "session_id": s.session_id,
        "buyer_id": s.buyer_id,
        "started_at": s.started_at.isoformat(),
        "ended_at": s.ended_at.isoformat(),
        "n_events": s.n_events,
        "n_views": s.n_views,
        "n_add": s.n_add,
        "n_remove": s.n_remove,
        "cart_value_vnd": s.cart_value_vnd,
        "distinct_items": s.distinct_items,
        "started_checkout": s.started_checkout,
        "completed_checkout": s.completed_checkout,
        "explicit_abandon": s.explicit_abandon,
    }


def session_from_dict(d: dict[str, object]) -> Session:
    return Session(
        session_id=_require_str(d, "session_id"),
        buyer_id=_require_str(d, "buyer_id"),
        started_at=datetime.fromisoformat(_require_str(d, "started_at")),
        ended_at=datetime.fromisoformat(_require_str(d, "ended_at")),
        n_events=_require_int(d, "n_events"),
        n_views=_require_int(d, "n_views"),
        n_add=_require_int(d, "n_add"),
        n_remove=_require_int(d, "n_remove"),
        cart_value_vnd=_require_int(d, "cart_value_vnd"),
        distinct_items=_require_int(d, "distinct_items"),
        started_checkout=_require_bool(d, "started_checkout"),
        completed_checkout=_require_bool(d, "completed_checkout"),
        explicit_abandon=_require_bool(d, "explicit_abandon"),
    )


def touch_to_dict(t: CampaignTouch) -> dict[str, object]:
    return {
        "touch_id": t.touch_id,
        "session_id": t.session_id,
        "buyer_id": t.buyer_id,
        "channel": t.channel.value,
        "scheduled_at": t.scheduled_at.isoformat(),
        "delay_minutes": t.delay_minutes,
    }


def touch_from_dict(d: dict[str, object]) -> CampaignTouch:
    return CampaignTouch(
        touch_id=_require_str(d, "touch_id"),
        session_id=_require_str(d, "session_id"),
        buyer_id=_require_str(d, "buyer_id"),
        channel=TouchChannel(_require_str(d, "channel")),
        scheduled_at=datetime.fromisoformat(_require_str(d, "scheduled_at")),
        delay_minutes=_require_int(d, "delay_minutes"),
    )


def attributed_to_dict(a: AttributedTouch) -> dict[str, object]:
    return {
        "touch": touch_to_dict(a.touch),
        "verdict": a.verdict.value,
        "conversion_event_id": a.conversion_event_id,
    }


def attributed_from_dict(d: dict[str, object]) -> AttributedTouch:
    raw_touch = d["touch"]
    if not isinstance(raw_touch, dict):
        raise TypeError("touch must be an object")
    return AttributedTouch(
        touch=touch_from_dict(raw_touch),
        verdict=AttributionVerdict(_require_str(d, "verdict")),
        conversion_event_id=_optional_str(d, "conversion_event_id"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(events: Iterable[Event]) -> str:
    return _dump(event_to_dict(e) for e in events)


def dump_sessions(sessions: Iterable[Session]) -> str:
    return _dump(session_to_dict(s) for s in sessions)


def dump_touches(touches: Iterable[CampaignTouch]) -> str:
    return _dump(touch_to_dict(t) for t in touches)


def dump_attributed(attributed: Iterable[AttributedTouch]) -> str:
    return _dump(attributed_to_dict(a) for a in attributed)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_events(text: str) -> Iterator[Event]:
    for d in _iter_lines(text):
        yield event_from_dict(d)


def load_sessions(text: str) -> Iterator[Session]:
    for d in _iter_lines(text):
        yield session_from_dict(d)


def load_touches(text: str) -> Iterator[CampaignTouch]:
    for d in _iter_lines(text):
        yield touch_from_dict(d)


def load_attributed(text: str) -> Iterator[AttributedTouch]:
    for d in _iter_lines(text):
        yield attributed_from_dict(d)


__all__ = [
    "attributed_from_dict",
    "attributed_to_dict",
    "dump_attributed",
    "dump_events",
    "dump_sessions",
    "dump_touches",
    "event_from_dict",
    "event_to_dict",
    "load_attributed",
    "load_events",
    "load_sessions",
    "load_touches",
    "session_from_dict",
    "session_to_dict",
    "touch_from_dict",
    "touch_to_dict",
]
