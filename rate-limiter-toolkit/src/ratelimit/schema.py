"""Rate-limiter schema — TokenBucket, LeakyBucket, SlidingWindow shapes.

All three limiters share the ``allow(key, now_ms)`` contract:

* ``allow`` returns ``True`` if the request is admitted, ``False`` if
  it should be throttled.
* All bookkeeping is keyed by an arbitrary string so the same limiter
  instance can throttle multiple users / IPs / API keys.

All limiters are *monotonic in time*: each call must pass a ``now_ms``
strictly ≥ the highest seen for that key. (We don't enforce a
process-wide clock; the caller picks the clock.)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TokenBucket:
    """Token bucket — capacity tokens, refilled at ``rate_per_sec``.

    Each ``allow(key, now_ms)`` first refills the bucket based on
    elapsed time, then deducts 1 token (returning True) or refuses
    (returning False) if the bucket is empty.

    Storage: per-key ``(tokens, last_refill_ms)``.
    """

    capacity: int
    rate_per_sec: float
    _state: dict[str, tuple[float, int]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.rate_per_sec <= 0:
            raise ValueError(
                f"rate_per_sec must be > 0, got {self.rate_per_sec}",
            )


@dataclass(slots=True)
class LeakyBucket:
    """Leaky bucket — queue of size ``capacity`` drained at ``rate_per_sec``.

    Each ``allow(key, now_ms)`` first leaks queued requests based on
    elapsed time, then adds 1 to the queue (admitting) or refuses
    (when full).

    Storage: per-key ``(queue_level, last_leak_ms)``.
    """

    capacity: int
    rate_per_sec: float
    _state: dict[str, tuple[float, int]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.rate_per_sec <= 0:
            raise ValueError(
                f"rate_per_sec must be > 0, got {self.rate_per_sec}",
            )


@dataclass(slots=True)
class SlidingWindowLog:
    """Sliding-window-log limiter — keeps timestamps of recent requests.

    Each ``allow(key, now_ms)`` evicts timestamps older than
    ``window_ms``, then admits if the remaining log has < ``capacity``
    entries (appending the new one) or refuses.

    Trade-off: O(capacity) memory per key, but no edge artifacts (no
    burst at window boundaries like fixed-window has).
    """

    capacity: int
    window_ms: int
    _state: dict[str, list[int]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.window_ms < 1:
            raise ValueError(f"window_ms must be >= 1, got {self.window_ms}")


__all__ = ["LeakyBucket", "SlidingWindowLog", "TokenBucket"]
