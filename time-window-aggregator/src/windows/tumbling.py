"""Tumbling windows — fixed-size, non-overlapping.

An event at ``ts_ms`` lands in exactly one tumbling window:

    window_index = ts_ms // width_ms
    window = [window_index · width, (window_index + 1) · width)

Useful for **non-overlapping period rollups** like "per-minute
request count" or "5-minute revenue total".
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from windows.schema import Window, WindowedAggregate, WindowKind

if TYPE_CHECKING:
    from windows.schema import Event


def assign_window(ts_ms: int, width_ms: int) -> Window:
    """Return the tumbling window containing ``ts_ms``."""
    if width_ms <= 0:
        raise ValueError(f"width_ms must be > 0, got {width_ms}")
    if ts_ms < 0:
        raise ValueError(f"ts_ms must be >= 0, got {ts_ms}")
    index = ts_ms // width_ms
    return Window(
        start_ms=index * width_ms,
        end_ms=(index + 1) * width_ms,
        kind=WindowKind.TUMBLING,
    )


def aggregate(
    events: list[Event],
    width_ms: int,
) -> list[WindowedAggregate]:
    """Aggregate events into per-(window, key) rollups.

    Output sorted by ``(window.start_ms, key)``.
    """
    if width_ms <= 0:
        raise ValueError(f"width_ms must be > 0, got {width_ms}")
    groups: dict[tuple[Window, str], list[Event]] = defaultdict(list)
    for e in events:
        win = assign_window(e.ts_ms, width_ms)
        groups[(win, e.key)].append(e)
    out: list[WindowedAggregate] = []
    for (window, key), bucket in groups.items():
        values = [e.value for e in bucket]
        out.append(
            WindowedAggregate(
                window=window,
                key=key,
                count=len(bucket),
                sum_value=sum(values),
                min_value=min(values),
                max_value=max(values),
            )
        )
    out.sort(key=lambda a: (a.window.start_ms, a.key))
    return out


__all__ = ["aggregate", "assign_window"]
