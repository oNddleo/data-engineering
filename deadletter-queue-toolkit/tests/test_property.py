"""Hypothesis property tests."""

from __future__ import annotations

import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dlq.retry import JitterMode, RetryPolicy, next_backoff_ms


@given(
    base=st.integers(min_value=1, max_value=10_000),
    multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    cap=st.integers(min_value=10_000, max_value=1_000_000),
    attempt=st.integers(min_value=0, max_value=20),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_full_jitter_in_bounds(base: int, multiplier: float, cap: int, attempt: int) -> None:
    """Full jitter returns a value in [0, capped_base]."""
    if cap < base:
        return  # invalid combo for this policy
    policy = RetryPolicy(
        max_attempts=30,
        base_ms=base,
        multiplier=multiplier,
        max_backoff_ms=cap,
        jitter=JitterMode.FULL,
    )
    rng = random.Random(0)
    expected_base = min(int(base * multiplier**attempt), cap)
    for _ in range(10):
        v = next_backoff_ms(policy, attempt, rng=rng)
        assert 0 <= v <= expected_base


@given(
    base=st.integers(min_value=2, max_value=10_000),
    multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    cap=st.integers(min_value=10_000, max_value=1_000_000),
    attempt=st.integers(min_value=0, max_value=20),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_equal_jitter_in_upper_half(base: int, multiplier: float, cap: int, attempt: int) -> None:
    """Equal jitter returns a value in [base/2, base]."""
    if cap < base:
        return
    policy = RetryPolicy(
        max_attempts=30,
        base_ms=base,
        multiplier=multiplier,
        max_backoff_ms=cap,
        jitter=JitterMode.EQUAL,
    )
    rng = random.Random(0)
    expected_base = min(int(base * multiplier**attempt), cap)
    half = expected_base // 2
    for _ in range(10):
        v = next_backoff_ms(policy, attempt, rng=rng)
        assert half <= v <= expected_base


@given(
    base=st.integers(min_value=1, max_value=10_000),
    multiplier=st.floats(min_value=1.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    cap=st.integers(min_value=10_000, max_value=1_000_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_no_jitter_monotone(base: int, multiplier: float, cap: int) -> None:
    """Without jitter, backoff is non-decreasing in attempt (until cap)."""
    if cap < base:
        return
    policy = RetryPolicy(
        max_attempts=30,
        base_ms=base,
        multiplier=multiplier,
        max_backoff_ms=cap,
        jitter=JitterMode.NONE,
    )
    prev = -1
    for attempt in range(20):
        v = next_backoff_ms(policy, attempt)
        assert v >= prev
        prev = v
