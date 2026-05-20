"""Token bucket algorithm.

Capacity = ``C`` tokens. Tokens refill at ``rate_per_sec`` (fractional
allowed). Each ``allow`` call:

1. Refill: ``tokens = min(capacity, tokens + (now − last) × rate)``
2. If tokens ≥ 1: ``tokens -= 1``, return ``True``.
3. Otherwise return ``False``.

This admits bursts up to ``capacity`` while enforcing a long-run rate
of ``rate_per_sec`` requests/second.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ratelimit.schema import TokenBucket


def allow(bucket: TokenBucket, key: str, now_ms: int) -> bool:
    """Try to consume one token from ``bucket[key]`` at time ``now_ms``."""
    if not key:
        raise ValueError("key must be non-empty")
    if now_ms < 0:
        raise ValueError(f"now_ms must be >= 0, got {now_ms}")

    state = bucket._state.get(key)
    if state is None:
        tokens = float(bucket.capacity)
        last_refill = now_ms
    else:
        tokens, last_refill = state
        if now_ms < last_refill:
            raise ValueError(
                f"now_ms {now_ms} earlier than last_refill {last_refill}",
            )
        elapsed_s = (now_ms - last_refill) / 1_000.0
        tokens = min(bucket.capacity, tokens + elapsed_s * bucket.rate_per_sec)

    if tokens >= 1.0:
        tokens -= 1.0
        bucket._state[key] = (tokens, now_ms)
        return True

    bucket._state[key] = (tokens, now_ms)
    return False


def remaining(bucket: TokenBucket, key: str, now_ms: int) -> float:
    """Current token count after a virtual refill, without consuming."""
    state = bucket._state.get(key)
    if state is None:
        return float(bucket.capacity)
    tokens, last_refill = state
    elapsed_s = max(0, now_ms - last_refill) / 1_000.0
    return min(bucket.capacity, tokens + elapsed_s * bucket.rate_per_sec)


__all__ = ["allow", "remaining"]
