"""Downstream backpressure monitor.

Workers call push() with a load factor in [0, 1].  The monitor aggregates
these signals into a rolling exponentially-weighted average.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class PressureSignal:
    timestamp: float
    source: str
    level: float  # 0 = no pressure … 1 = saturated


class BackpressureMonitor:
    """Collects pressure signals and exposes a weighted-average level."""

    def __init__(self, window_seconds: float = 5.0) -> None:
        self.window_seconds = window_seconds
        self._signals: deque[PressureSignal] = deque()
        self._callback: Callable[[float], None] | None = None

    # ── registration ─────────────────────────────────────────────────────────

    def on_pressure_change(self, callback: Callable[[float], None]) -> None:
        self._callback = callback

    # ── mutation ─────────────────────────────────────────────────────────────

    def push(self, source: str, level: float) -> None:
        level = max(0.0, min(1.0, level))
        self._signals.append(
            PressureSignal(timestamp=time.monotonic(), source=source, level=level)
        )
        self._evict()
        if self._callback is not None:
            self._callback(self.current_level())

    def clear(self) -> None:
        self._signals.clear()

    # ── queries ──────────────────────────────────────────────────────────────

    def current_level(self) -> float:
        self._evict()
        if not self._signals:
            return 0.0
        now = time.monotonic()
        half_life = self.window_seconds / 3.0
        w_sum = 0.0
        v_sum = 0.0
        for sig in self._signals:
            age = now - sig.timestamp
            w = 2.0 ** (-age / half_life)
            w_sum += w
            v_sum += w * sig.level
        return v_sum / w_sum if w_sum > 0.0 else 0.0

    def is_saturated(self, threshold: float = 0.85) -> bool:
        return self.current_level() >= threshold

    # ── private ──────────────────────────────────────────────────────────────

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        while self._signals and self._signals[0].timestamp < cutoff:
            self._signals.popleft()
