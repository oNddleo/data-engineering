"""Simulate request patterns against rate limiters."""

from __future__ import annotations

from dataclasses import dataclass

from ratelimiter.sliding_window import SlidingWindowCounter
from ratelimiter.token_bucket import TokenBucket


@dataclass
class SimResult:
    total_requests: int
    allowed: int
    rejected: int
    algorithm: str


def simulate_token_bucket(
    capacity: float = 10.0,
    refill_rate: float = 5.0,
    n_requests: int = 100,
    request_interval_s: float = 0.1,
    tokens_per_request: int = 1,
) -> SimResult:
    """Simulate requests against a token bucket using a manual clock."""
    t = 0.0

    def clock() -> float:
        return t

    tb = TokenBucket(capacity=capacity, refill_rate=refill_rate, _clock=clock)
    allowed = 0
    rejected = 0

    for _ in range(n_requests):
        t += request_interval_s
        if tb.acquire(tokens_per_request):
            allowed += 1
        else:
            rejected += 1

    return SimResult(
        total_requests=n_requests,
        allowed=allowed,
        rejected=rejected,
        algorithm="token_bucket",
    )


def simulate_sliding_window(
    limit: int = 10,
    window_s: float = 1.0,
    n_requests: int = 100,
    request_interval_s: float = 0.05,
) -> SimResult:
    """Simulate requests against a sliding window counter using a manual clock."""
    t = 0.0

    def clock() -> float:
        return t

    sw = SlidingWindowCounter(limit=limit, window_s=window_s, _clock=clock)
    allowed = 0
    rejected = 0

    for _ in range(n_requests):
        t += request_interval_s
        if sw.acquire():
            allowed += 1
        else:
            rejected += 1

    return SimResult(
        total_requests=n_requests,
        allowed=allowed,
        rejected=rejected,
        algorithm="sliding_window",
    )
