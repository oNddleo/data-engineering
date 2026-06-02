"""Property-based tests for rate limiters."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ratelimiter.sliding_window import SlidingWindowCounter
from ratelimiter.token_bucket import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@given(
    capacity=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    n=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_token_bucket_tokens_never_exceed_capacity(
    capacity: float, refill_rate: float, n: int
) -> None:
    clock = FakeClock()
    tb = TokenBucket(capacity=capacity, refill_rate=refill_rate, _clock=clock)
    for _ in range(n):
        clock.t += 0.1
        tb.acquire(1)
        assert tb.tokens <= capacity + 1e-9


@given(
    capacity=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30)
def test_token_bucket_empty_never_goes_negative(capacity: float) -> None:
    clock = FakeClock()
    tb = TokenBucket(capacity=capacity, refill_rate=1.0, _clock=clock)
    # Drain completely
    tb.acquire(int(capacity))
    assert tb.tokens >= 0.0


@given(
    limit=st.integers(min_value=1, max_value=100),
    n_requests=st.integers(min_value=1, max_value=200),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_sliding_window_allowed_never_exceeds_limit(limit: int, n_requests: int) -> None:
    """In any 1-second window, allowed requests never exceed limit."""
    clock = FakeClock()
    sw = SlidingWindowCounter(limit=limit, window_s=1.0, _clock=clock)
    # All requests in same window
    allowed = 0
    for _ in range(n_requests):
        clock.t += 0.001  # within 1s window
        if sw.acquire():
            allowed += 1
    assert allowed <= limit


@given(
    capacity=st.floats(min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30)
def test_time_to_tokens_ge_zero(capacity: float, refill_rate: float) -> None:
    clock = FakeClock()
    tb = TokenBucket(capacity=capacity, refill_rate=refill_rate, _clock=clock)
    tb.acquire(int(capacity))
    wait = tb.time_to_tokens(1)
    assert wait >= 0.0
