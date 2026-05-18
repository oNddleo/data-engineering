"""JSONL codec for Event / EmittedRecord / BufferStats."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from latebuf.schema import (
    BufferStats,
    EmittedRecord,
    Event,
    EventDisposition,
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


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


# ---------- Event -----------------------------------------------------------


def event_to_dict(e: Event) -> dict[str, object]:
    return {
        "event_id": e.event_id,
        "event_time": e.event_time.isoformat(),
        "ingest_time": e.ingest_time.isoformat(),
        "payload": e.payload,
        "is_punctuation": e.is_punctuation,
    }


def event_from_dict(d: dict[str, object]) -> Event:
    return Event(
        event_id=_require_str(d, "event_id"),
        event_time=datetime.fromisoformat(_require_str(d, "event_time")),
        ingest_time=datetime.fromisoformat(_require_str(d, "ingest_time")),
        payload=_require_str(d, "payload") if "payload" in d else "",
        is_punctuation=_require_bool(d, "is_punctuation") if "is_punctuation" in d else False,
    )


# ---------- EmittedRecord ----------------------------------------------------


def emitted_to_dict(r: EmittedRecord) -> dict[str, object]:
    return {
        "event": event_to_dict(r.event),
        "disposition": r.disposition.value,
        "lateness_seconds": r.lateness_seconds,
    }


def emitted_from_dict(d: dict[str, object]) -> EmittedRecord:
    ev = d["event"]
    if not isinstance(ev, dict):
        raise TypeError("event must be dict")
    return EmittedRecord(
        event=event_from_dict(ev),
        disposition=EventDisposition(_require_str(d, "disposition")),
        lateness_seconds=_require_int(d, "lateness_seconds"),
    )


# ---------- BufferStats ------------------------------------------------------


def stats_to_dict(s: BufferStats) -> dict[str, object]:
    return {
        "n_accepted": s.n_accepted,
        "n_emitted": s.n_emitted,
        "n_dead_lettered": s.n_dead_lettered,
        "n_still_buffered": s.n_still_buffered,
        "max_lateness_seconds": s.max_lateness_seconds,
        "median_lateness_seconds": s.median_lateness_seconds,
        "p99_lateness_seconds": s.p99_lateness_seconds,
        "final_watermark": s.final_watermark.isoformat() if s.final_watermark is not None else None,
        "drop_rate_pct": round(s.drop_rate_pct, 2),
    }


def stats_from_dict(d: dict[str, object]) -> BufferStats:
    wm = d.get("final_watermark")
    final_wm = datetime.fromisoformat(wm) if isinstance(wm, str) else None
    return BufferStats(
        n_accepted=_require_int(d, "n_accepted"),
        n_emitted=_require_int(d, "n_emitted"),
        n_dead_lettered=_require_int(d, "n_dead_lettered"),
        n_still_buffered=_require_int(d, "n_still_buffered"),
        max_lateness_seconds=_require_int(d, "max_lateness_seconds"),
        median_lateness_seconds=_require_int(d, "median_lateness_seconds"),
        p99_lateness_seconds=_require_int(d, "p99_lateness_seconds"),
        final_watermark=final_wm,
    )


# ---------- dump / load ------------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_events(items: Iterable[Event]) -> str:
    return _dump(event_to_dict(e) for e in items)


def dump_emitted(items: Iterable[EmittedRecord]) -> str:
    return _dump(emitted_to_dict(r) for r in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_events(text: str) -> list[Event]:
    return [event_from_dict(d) for d in _iter_lines(text)]


def load_emitted(text: str) -> list[EmittedRecord]:
    return [emitted_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_emitted",
    "dump_events",
    "emitted_from_dict",
    "emitted_to_dict",
    "event_from_dict",
    "event_to_dict",
    "load_emitted",
    "load_events",
    "stats_from_dict",
    "stats_to_dict",
]
