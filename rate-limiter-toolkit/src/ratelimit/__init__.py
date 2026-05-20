"""rate-limiter-toolkit — token bucket, leaky bucket, sliding-window log."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from ratelimit.leaky_bucket import allow as leaky_allow
    from ratelimit.leaky_bucket import queue_depth
    from ratelimit.schema import LeakyBucket, SlidingWindowLog, TokenBucket
    from ratelimit.simulator import burst_then_idle, constant_rate
    from ratelimit.sliding_window import allow as sliding_allow
    from ratelimit.sliding_window import current_count
    from ratelimit.token_bucket import allow as token_allow
    from ratelimit.token_bucket import remaining


_LAZY: dict[str, tuple[str, str]] = {
    "LeakyBucket": ("ratelimit.schema", "LeakyBucket"),
    "SlidingWindowLog": ("ratelimit.schema", "SlidingWindowLog"),
    "TokenBucket": ("ratelimit.schema", "TokenBucket"),
    "burst_then_idle": ("ratelimit.simulator", "burst_then_idle"),
    "constant_rate": ("ratelimit.simulator", "constant_rate"),
    "current_count": ("ratelimit.sliding_window", "current_count"),
    "leaky_allow": ("ratelimit.leaky_bucket", "allow"),
    "queue_depth": ("ratelimit.leaky_bucket", "queue_depth"),
    "remaining": ("ratelimit.token_bucket", "remaining"),
    "sliding_allow": ("ratelimit.sliding_window", "allow"),
    "token_allow": ("ratelimit.token_bucket", "allow"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LeakyBucket",
    "SlidingWindowLog",
    "TokenBucket",
    "__version__",
    "burst_then_idle",
    "constant_rate",
    "current_count",
    "leaky_allow",
    "queue_depth",
    "remaining",
    "sliding_allow",
    "token_allow",
]
