"""Event builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from latebuf.schema import VN_TZ, Event

DEFAULT_TS = datetime(2026, 5, 18, 9, 0, 0, tzinfo=VN_TZ)


def make_event(**overrides: Any) -> Event:
    """Build an Event with sane defaults."""
    defaults: dict[str, Any] = {
        "event_id": "E-0001",
        "event_time": DEFAULT_TS,
        "ingest_time": DEFAULT_TS,
        "payload": "",
        "is_punctuation": False,
    }
    defaults.update(overrides)
    return Event(**defaults)


def event_at(
    event_id: str,
    event_time_offset_s: int,
    ingest_time_offset_s: int | None = None,
    *,
    is_punctuation: bool = False,
) -> Event:
    """Build an Event at an offset (seconds) from ``DEFAULT_TS``.

    If ``ingest_time_offset_s`` is ``None``, it defaults to
    ``event_time_offset_s`` (in-order arrival, no lateness).
    """
    if ingest_time_offset_s is None:
        ingest_time_offset_s = event_time_offset_s
    return make_event(
        event_id=event_id,
        event_time=DEFAULT_TS + timedelta(seconds=event_time_offset_s),
        ingest_time=DEFAULT_TS + timedelta(seconds=ingest_time_offset_s),
        is_punctuation=is_punctuation,
    )


__all__ = ["DEFAULT_TS", "event_at", "make_event"]
