"""Sliding windows — fixed-size, overlapping by stride.

An event at ``ts_ms`` lands in every sliding window
``[k·stride, k·stride + width)`` that contains it. With
``stride < width`` an event participates in ``width // stride``
overlapping windows.

Common use case: trailing-N-minute averages with M-minute refresh
(e.g. "5-minute trailing latency p99 recomputed every 1 minute" →
width=300000, stride=60000).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from windows.schema import Window, WindowedAggregate, WindowKind

if TYPE_CHECKING:
    from windows.schema import Event


def windows_for(ts_ms: int, width_ms: int, stride_ms: int) -> list[Window]:
    """Return every sliding window that contains ``ts_ms``."""
    if width_ms <= 0:
        raise ValueError(f"width_ms must be > 0, got {width_ms}")
    if stride_ms <= 0:
        raise ValueError(f"stride_ms must be > 0, got {stride_ms}")
    if ts_ms < 0:
        raise ValueError(f"ts_ms must be >= 0, got {ts_ms}")
    # The window starts at k·stride for k in [max(0, ceil((ts-width+1)/stride)),
    # ts // stride].
    last_k = ts_ms // stride_ms
    # earliest start s.t. s <= ts AND s + width > ts → s > ts - width
    first_k_raw = (ts_ms - width_ms + stride_ms) // stride_ms
    first_k = max(0, first_k_raw)
    if first_k > last_k:
        return []
    out: list[Window] = []
    for k in range(first_k, last_k + 1):
        start = k * stride_ms
        end = start + width_ms
        if start <= ts_ms < end:
            out.append(Window(start_ms=start, end_ms=end, kind=WindowKind.SLIDING))
    return out


def aggregate(
    events: list[Event],
    width_ms: int,
    stride_ms: int,
) -> list[WindowedAggregate]:
    """Aggregate events into per-(window, key) rollups for sliding windows."""
    if width_ms <= 0:
        raise ValueError(f"width_ms must be > 0, got {width_ms}")
    if stride_ms <= 0:
        raise ValueError(f"stride_ms must be > 0, got {stride_ms}")
    groups: dict[tuple[Window, str], list[int]] = defaultdict(list)
    for e in events:
        for win in windows_for(e.ts_ms, width_ms, stride_ms):
            groups[(win, e.key)].append(e.value)
    out: list[WindowedAggregate] = []
    for (window, key), values in groups.items():
        out.append(
            WindowedAggregate(
                window=window,
                key=key,
                count=len(values),
                sum_value=sum(values),
                min_value=min(values),
                max_value=max(values),
            )
        )
    out.sort(key=lambda a: (a.window.start_ms, a.key))
    return out


__all__ = ["aggregate", "windows_for"]
