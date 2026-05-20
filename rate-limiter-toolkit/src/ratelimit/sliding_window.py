"""Sliding-window log algorithm.

Per key, maintain a sorted list of recent admission timestamps.
On each ``allow``:

1. Evict timestamps older than ``now − window_ms``.
2. If remaining log has < ``capacity`` entries: append ``now``,
   return ``True``.
3. Otherwise return ``False``.

No edge artifacts (unlike fixed-window, which allows ``2 × capacity``
in a tiny window across the boundary). Cost: O(capacity) memory and
O(capacity) per call (the evict scan).
"""

from __future__ import annotations

from bisect import bisect_left
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ratelimit.schema import SlidingWindowLog


def allow(limiter: SlidingWindowLog, key: str, now_ms: int) -> bool:
    """Try to log one request at ``now_ms`` against the sliding window."""
    if not key:
        raise ValueError("key must be non-empty")
    if now_ms < 0:
        raise ValueError(f"now_ms must be >= 0, got {now_ms}")

    log = limiter._state.setdefault(key, [])
    cutoff = now_ms - limiter.window_ms
    # Evict timestamps older than cutoff using binary search.
    cutoff_idx = bisect_left(log, cutoff + 1)
    if cutoff_idx > 0:
        del log[:cutoff_idx]

    if len(log) < limiter.capacity:
        log.append(now_ms)
        return True
    return False


def current_count(limiter: SlidingWindowLog, key: str, now_ms: int) -> int:
    """Number of admissions in the trailing ``window_ms`` ending at ``now_ms``."""
    log = limiter._state.get(key, [])
    cutoff = now_ms - limiter.window_ms
    cutoff_idx = bisect_left(log, cutoff + 1)
    return len(log) - cutoff_idx


__all__ = ["allow", "current_count"]
