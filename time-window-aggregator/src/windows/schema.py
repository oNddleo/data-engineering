"""Schema for time-windowed streaming aggregation.

Three canonical windowing strategies:

| Kind       | Definition                                              |
| ---------- | ------------------------------------------------------- |
| TUMBLING   | Fixed-size, non-overlapping. ``W = [n·s, (n+1)·s)``     |
| SLIDING    | Fixed-size, overlapping by stride ``r``. Every ``r`` ms |
| SESSION    | Variable-size. Grouped by activity gap ≤ ``timeout``    |

We model events as ``(key, value, ts_ms)`` tuples and produce
``WindowedAggregate`` rollups carrying ``(window, key, count, sum,
min, max, distinct_values)``.

All timestamps are milliseconds since some epoch (we don't fix the
epoch — callers are free to use UNIX time, monotonic clocks, or
trace-local time). Windows are inclusive of ``start_ms``, exclusive
of ``end_ms`` — the standard half-open interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WindowKind(str, Enum):
    """Three canonical windowing strategies."""

    TUMBLING = "TUMBLING"
    SLIDING = "SLIDING"
    SESSION = "SESSION"


@dataclass(frozen=True, slots=True)
class Window:
    """One half-open time interval ``[start_ms, end_ms)``."""

    start_ms: int
    end_ms: int
    kind: WindowKind

    def __post_init__(self) -> None:
        if self.start_ms < 0:
            raise ValueError(f"start_ms must be >= 0, got {self.start_ms}")
        if self.end_ms <= self.start_ms:
            raise ValueError(
                f"end_ms ({self.end_ms}) must be > start_ms ({self.start_ms})",
            )

    @property
    def width_ms(self) -> int:
        """Window width in milliseconds."""
        return self.end_ms - self.start_ms

    def contains(self, ts_ms: int) -> bool:
        """``True`` iff ``ts_ms`` lies in the half-open interval."""
        return self.start_ms <= ts_ms < self.end_ms


@dataclass(frozen=True, slots=True)
class Event:
    """One stream event.

    ``value`` is the numeric measurement to aggregate (latency,
    bytes, dollar amount, ...). For count-only flows, callers can
    set ``value=1`` uniformly.
    """

    key: str
    value: int
    ts_ms: int

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key must be non-empty")
        if self.ts_ms < 0:
            raise ValueError(f"ts_ms must be >= 0, got {self.ts_ms}")


@dataclass(frozen=True, slots=True)
class WindowedAggregate:
    """Aggregate rollup for one (window, key) cell."""

    window: Window
    key: str
    count: int
    sum_value: int
    min_value: int
    max_value: int

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"count must be >= 0, got {self.count}")
        if self.count > 0 and self.min_value > self.max_value:
            raise ValueError(
                f"min_value ({self.min_value}) > max_value ({self.max_value})",
            )

    @property
    def avg_value(self) -> float:
        """Mean value across the window (0 if count == 0)."""
        return self.sum_value / self.count if self.count > 0 else 0.0


__all__ = [
    "Event",
    "Window",
    "WindowKind",
    "WindowedAggregate",
]
