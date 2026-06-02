"""JSONL codec for Event + WindowedAggregate."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from windows.schema import Event, Window, WindowedAggregate, WindowKind

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


def _require_dict(d: dict[str, object], key: str) -> dict[str, object]:
    v = d[key]
    if not isinstance(v, dict):
        raise TypeError(f"{key} must be dict, got {type(v).__name__}")
    return v


def event_to_dict(e: Event) -> dict[str, object]:
    return {"key": e.key, "value": e.value, "ts_ms": e.ts_ms}


def event_from_dict(d: dict[str, object]) -> Event:
    return Event(
        key=_require_str(d, "key"),
        value=_require_int(d, "value"),
        ts_ms=_require_int(d, "ts_ms"),
    )


def window_to_dict(w: Window) -> dict[str, object]:
    return {
        "start_ms": w.start_ms,
        "end_ms": w.end_ms,
        "kind": w.kind.value,
    }


def window_from_dict(d: dict[str, object]) -> Window:
    return Window(
        start_ms=_require_int(d, "start_ms"),
        end_ms=_require_int(d, "end_ms"),
        kind=WindowKind(_require_str(d, "kind")),
    )


def agg_to_dict(a: WindowedAggregate) -> dict[str, object]:
    return {
        "window": window_to_dict(a.window),
        "key": a.key,
        "count": a.count,
        "sum_value": a.sum_value,
        "min_value": a.min_value,
        "max_value": a.max_value,
    }


def agg_from_dict(d: dict[str, object]) -> WindowedAggregate:
    return WindowedAggregate(
        window=window_from_dict(_require_dict(d, "window")),
        key=_require_str(d, "key"),
        count=_require_int(d, "count"),
        sum_value=_require_int(d, "sum_value"),
        min_value=_require_int(d, "min_value"),
        max_value=_require_int(d, "max_value"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[Event]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_aggs(items: Iterable[WindowedAggregate]) -> str:
    return _dump(agg_to_dict(a) for a in items)


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


def load_events(text: str) -> list[Event]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_aggs(text: str) -> list[WindowedAggregate]:
    return [agg_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "agg_from_dict",
    "agg_to_dict",
    "dump_aggs",
    "dump_events",
    "event_from_dict",
    "event_to_dict",
    "load_aggs",
    "load_events",
    "window_from_dict",
    "window_to_dict",
]
