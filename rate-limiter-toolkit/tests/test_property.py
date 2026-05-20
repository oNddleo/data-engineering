"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ratelimit.leaky_bucket import allow as leaky_allow
from ratelimit.schema import LeakyBucket, SlidingWindowLog, TokenBucket
from ratelimit.sliding_window import allow as sliding_allow
from ratelimit.token_bucket import allow as token_allow

_capacity = st.integers(min_value=1, max_value=100)
_rate = st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)


@given(_capacity, _rate, st.integers(min_value=0, max_value=10_000))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_token_burst_capped_at_capacity(
    cap: int,
    rate: float,
    n_requests: int,
) -> None:
    """A back-to-back burst at t=0 admits at most ``capacity`` requests."""
    tb = TokenBucket(capacity=cap, rate_per_sec=rate)
    admitted = sum(1 for _ in range(n_requests) if token_allow(tb, "k", 0))
    assert admitted <= cap


@given(_capacity, _rate, st.integers(min_value=0, max_value=10_000))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_leaky_burst_capped_at_capacity(
    cap: int,
    rate: float,
    n_requests: int,
) -> None:
    lb = LeakyBucket(capacity=cap, rate_per_sec=rate)
    admitted = sum(1 for _ in range(n_requests) if leaky_allow(lb, "k", 0))
    assert admitted <= cap


@given(
    _capacity,
    st.integers(min_value=1, max_value=10_000),
    st.integers(min_value=0, max_value=10_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_sliding_capped_at_capacity(
    cap: int,
    window: int,
    n_requests: int,
) -> None:
    """Sliding-log admits ≤ capacity requests in any window."""
    sw = SlidingWindowLog(capacity=cap, window_ms=window)
    admitted = sum(1 for _ in range(n_requests) if sliding_allow(sw, "k", 0))
    assert admitted <= cap


@given(
    _capacity,
    _rate,
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=0, max_value=10_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_token_keys_isolated(
    cap: int,
    rate: float,
    n_keys: int,
    n_per_key: int,
) -> None:
    """Each key's admission count is independently capped at capacity."""
    tb = TokenBucket(capacity=cap, rate_per_sec=rate)
    for k in range(n_keys):
        key = f"key-{k}"
        admitted = sum(1 for _ in range(n_per_key) if token_allow(tb, key, 0))
        assert admitted <= cap


@given(_capacity, _rate)
def test_token_steady_state_admits_some(cap: int, rate: float) -> None:
    """Issuing at twice the rate, we still admit > 0 long-run."""
    tb = TokenBucket(capacity=cap, rate_per_sec=rate)
    # Use generous interval (×2 of rate) to ensure positive admit rate
    # despite int truncation.
    interval_ms = max(2, int(2_000 / rate))
    n = 50
    admitted = sum(1 for i in range(n) if token_allow(tb, "k", i * interval_ms))
    assert admitted > 0
