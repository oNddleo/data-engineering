"""Sliding Window Counter rate limiter.

Maintains a precise count of events in the past `window_s` seconds
using a deque of timestamps. Memory: O(max events in window).

Clock is injectable for deterministic testing.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class SlidingWindowCounter:
    """Sliding window rate limiter.

    Args:
        limit:      Maximum number of events allowed in *window_s* seconds.
        window_s:   Length of the sliding window in seconds.
        name:       Human-readable label.
        _clock:     Callable returning current time in seconds (injectable).
    """

    limit: int
    window_s: float
    name: str = "default"
    _clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    _timestamps: deque[float] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be >= 1")
        if self.window_s <= 0:
            raise ValueError("window_s must be > 0")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_count(self) -> int:
        """Number of events in the current window."""
        self._evict_old()
        return len(self._timestamps)

    def acquire(self) -> bool:
        """Try to record one event.

        Returns:
            True if allowed (under limit), False if limit exceeded.
        """
        self._evict_old()
        if len(self._timestamps) < self.limit:
            self._timestamps.append(self._clock())
            return True
        return False

    def acquire_or_raise(self) -> None:
        """Record one event or raise RateLimitExceeded."""
        from ratelimiter.token_bucket import RateLimitExceeded

        self._evict_old()
        if len(self._timestamps) < self.limit:
            self._timestamps.append(self._clock())
        else:
            raise RateLimitExceeded(self.name, 1, 0.0)

    def time_to_next_slot(self) -> float:
        """Seconds until the oldest event falls out of the window (0 if slot available)."""
        self._evict_old()
        if len(self._timestamps) < self.limit:
            return 0.0
        oldest = self._timestamps[0]
        now = self._clock()
        return max(0.0, oldest + self.window_s - now)

    def snapshot(self) -> dict[str, object]:
        """Serialisable snapshot."""
        self._evict_old()
        return {
            "name": self.name,
            "limit": self.limit,
            "window_s": self.window_s,
            "current_count": len(self._timestamps),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_old(self) -> None:
        cutoff = self._clock() - self.window_s
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
