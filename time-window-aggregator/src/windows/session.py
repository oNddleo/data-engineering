"""Session windows — variable-size, gap-based.

Per key, consecutive events whose inter-arrival gap is ≤ ``timeout_ms``
belong to the same session. As soon as a gap exceeds the timeout,
the current session closes and a new one opens.

Useful for user-activity sessionisation: "all activity from user X
within 30 minutes of inactivity is one session" → ``timeout_ms = 1_800_000``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from windows.schema import Window, WindowedAggregate, WindowKind

if TYPE_CHECKING:
    from windows.schema import Event


def aggregate(
    events: list[Event],
    timeout_ms: int,
) -> list[WindowedAggregate]:
    """Group per-key events into session windows by activity gap.

    Output sorted by ``(window.start_ms, key)``.
    """
    if timeout_ms <= 0:
        raise ValueError(f"timeout_ms must be > 0, got {timeout_ms}")
    per_key: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        per_key[e.key].append(e)

    out: list[WindowedAggregate] = []
    for key, ordered in per_key.items():
        ordered = sorted(ordered, key=lambda x: x.ts_ms)
        # Walk; close a session when the gap to the next event exceeds timeout.
        current_events: list[Event] = []
        current_end_ts: int | None = None
        for ev in ordered:
            if current_end_ts is None:
                current_events.append(ev)
                current_end_ts = ev.ts_ms
                continue
            gap = ev.ts_ms - current_end_ts
            if gap <= timeout_ms:
                current_events.append(ev)
                current_end_ts = ev.ts_ms
            else:
                out.append(_close_session(current_events, key))
                current_events = [ev]
                current_end_ts = ev.ts_ms
        if current_events:
            out.append(_close_session(current_events, key))
    out.sort(key=lambda a: (a.window.start_ms, a.key))
    return out


def _close_session(events: list[Event], key: str) -> WindowedAggregate:
    """Build a windowed aggregate from a session's contained events."""
    start = events[0].ts_ms
    # End is exclusive; the last event must be inside the window, so we
    # bump by 1 ms so the half-open [start, end) actually includes it.
    end = events[-1].ts_ms + 1
    values = [e.value for e in events]
    return WindowedAggregate(
        window=Window(start_ms=start, end_ms=end, kind=WindowKind.SESSION),
        key=key,
        count=len(events),
        sum_value=sum(values),
        min_value=min(values),
        max_value=max(values),
    )


__all__ = ["aggregate"]
