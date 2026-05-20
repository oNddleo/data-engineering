"""Leaky bucket algorithm.

Queue depth ≤ ``capacity``. Items leak at ``rate_per_sec``. Each
``allow`` call:

1. Leak: ``queue = max(0, queue − (now − last) × rate)``
2. If queue < capacity: ``queue += 1``, return ``True``.
3. Otherwise return ``False``.

Smooths bursts into a steady output rate — every admitted request is
guaranteed to leak out at ``rate_per_sec`` regardless of input
bursts. Useful when downstream depends on a steady arrival rate
(payment processors, SMS gateways).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ratelimit.schema import LeakyBucket


def allow(bucket: LeakyBucket, key: str, now_ms: int) -> bool:
    """Try to enqueue one request into ``bucket[key]``."""
    if not key:
        raise ValueError("key must be non-empty")
    if now_ms < 0:
        raise ValueError(f"now_ms must be >= 0, got {now_ms}")

    state = bucket._state.get(key)
    if state is None:
        queue = 0.0
        last_leak = now_ms
    else:
        queue, last_leak = state
        if now_ms < last_leak:
            raise ValueError(
                f"now_ms {now_ms} earlier than last_leak {last_leak}",
            )
        elapsed_s = (now_ms - last_leak) / 1_000.0
        queue = max(0.0, queue - elapsed_s * bucket.rate_per_sec)

    if queue < bucket.capacity:
        queue += 1.0
        bucket._state[key] = (queue, now_ms)
        return True

    bucket._state[key] = (queue, now_ms)
    return False


def queue_depth(bucket: LeakyBucket, key: str, now_ms: int) -> float:
    """Current queue depth after a virtual leak."""
    state = bucket._state.get(key)
    if state is None:
        return 0.0
    queue, last_leak = state
    elapsed_s = max(0, now_ms - last_leak) / 1_000.0
    return max(0.0, queue - elapsed_s * bucket.rate_per_sec)


__all__ = ["allow", "queue_depth"]
