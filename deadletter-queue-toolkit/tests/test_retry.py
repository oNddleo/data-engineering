"""RetryPolicy + backoff math."""

from __future__ import annotations

import random

import pytest

from dlq.retry import JitterMode, RetryPolicy, next_backoff_ms, should_retry


def test_no_jitter_exponential() -> None:
    policy = RetryPolicy(
        max_attempts=10, base_ms=100, multiplier=2.0, max_backoff_ms=100_000, jitter=JitterMode.NONE
    )
    assert next_backoff_ms(policy, 0) == 100
    assert next_backoff_ms(policy, 1) == 200
    assert next_backoff_ms(policy, 2) == 400
    assert next_backoff_ms(policy, 3) == 800


def test_no_jitter_capped_at_max() -> None:
    policy = RetryPolicy(
        max_attempts=20, base_ms=100, multiplier=2.0, max_backoff_ms=1000, jitter=JitterMode.NONE
    )
    # 100, 200, 400, 800, 1600 → cap, so attempt 4 onwards is 1000.
    assert next_backoff_ms(policy, 4) == 1000
    assert next_backoff_ms(policy, 10) == 1000


def test_full_jitter_in_range() -> None:
    """Full jitter: result is always in [0, base_backoff]."""
    policy = RetryPolicy(base_ms=100, max_backoff_ms=10_000, jitter=JitterMode.FULL)
    rng = random.Random(0)
    for attempt in range(5):
        # No-jitter base for this attempt:
        base = min(int(policy.base_ms * policy.multiplier**attempt), policy.max_backoff_ms)
        for _ in range(100):
            v = next_backoff_ms(policy, attempt, rng=rng)
            assert 0 <= v <= base


def test_equal_jitter_in_range() -> None:
    """Equal jitter: result is in [base/2, base]."""
    policy = RetryPolicy(base_ms=100, max_backoff_ms=10_000, jitter=JitterMode.EQUAL)
    rng = random.Random(0)
    for attempt in range(5):
        base = min(int(policy.base_ms * policy.multiplier**attempt), policy.max_backoff_ms)
        for _ in range(100):
            v = next_backoff_ms(policy, attempt, rng=rng)
            assert base // 2 <= v <= base


def test_full_jitter_mean_is_half_base() -> None:
    """Statistical sanity: full-jitter mean ≈ base/2."""
    policy = RetryPolicy(base_ms=1000, max_backoff_ms=10_000, jitter=JitterMode.FULL)
    rng = random.Random(0)
    samples = [next_backoff_ms(policy, 0, rng=rng) for _ in range(2000)]
    mean = sum(samples) / len(samples)
    assert 400 <= mean <= 600


def test_should_retry() -> None:
    policy = RetryPolicy(max_attempts=3)
    assert should_retry(policy, 1) is True
    assert should_retry(policy, 2) is True
    assert should_retry(policy, 3) is False
    assert should_retry(policy, 100) is False


def test_should_retry_validates_attempt() -> None:
    policy = RetryPolicy(max_attempts=3)
    with pytest.raises(ValueError):
        should_retry(policy, 0)


def test_next_backoff_validates_attempt() -> None:
    policy = RetryPolicy()
    with pytest.raises(ValueError):
        next_backoff_ms(policy, -1)


@pytest.mark.parametrize(
    ("kwargs", "expectation"),
    [
        ({"max_attempts": 0}, ValueError),
        ({"base_ms": -1}, ValueError),
        ({"multiplier": 0.5}, ValueError),
        ({"max_backoff_ms": 50, "base_ms": 100}, ValueError),
    ],
)
def test_policy_validation(kwargs: dict[str, int | float], expectation: type[Exception]) -> None:
    with pytest.raises(expectation):
        RetryPolicy(**kwargs)  # type: ignore[arg-type]
