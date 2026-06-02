"""Rate limiter toolkit: token bucket and sliding window algorithms."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "TokenBucket": ("ratelimiter.token_bucket", "TokenBucket"),
        "SlidingWindowCounter": ("ratelimiter.sliding_window", "SlidingWindowCounter"),
        "RateLimitExceeded": ("ratelimiter.token_bucket", "RateLimitExceeded"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["TokenBucket", "SlidingWindowCounter", "RateLimitExceeded"]
