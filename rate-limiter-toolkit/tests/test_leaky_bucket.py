"""Leaky bucket tests."""

from __future__ import annotations

import pytest

from ratelimit.leaky_bucket import allow, queue_depth
from ratelimit.schema import LeakyBucket


def test_initial_empty_queue() -> None:
    lb = LeakyBucket(capacity=10, rate_per_sec=1.0)
    assert queue_depth(lb, "k1", 0) == 0.0


def test_admits_until_full() -> None:
    lb = LeakyBucket(capacity=3, rate_per_sec=1.0)
    assert allow(lb, "k1", 0) is True
    assert allow(lb, "k1", 0) is True
    assert allow(lb, "k1", 0) is True
    # 4th request at t=0 finds queue full.
    assert allow(lb, "k1", 0) is False


def test_leaks_over_time() -> None:
    """After 1 second at 1/s rate, queue depth drops by 1."""
    lb = LeakyBucket(capacity=3, rate_per_sec=1.0)
    for _ in range(3):
        allow(lb, "k1", 0)
    assert allow(lb, "k1", 0) is False
    # 1 second passes → 1 item drains; new request admitted.
    assert allow(lb, "k1", 1_000) is True


def test_leak_floors_at_zero() -> None:
    """Long idle doesn't drive queue negative."""
    lb = LeakyBucket(capacity=5, rate_per_sec=10.0)
    allow(lb, "k1", 0)
    # 10 seconds idle.
    assert queue_depth(lb, "k1", 10_000) == 0.0


def test_per_key_isolation() -> None:
    lb = LeakyBucket(capacity=2, rate_per_sec=1.0)
    allow(lb, "k1", 0)
    allow(lb, "k1", 0)
    assert allow(lb, "k1", 0) is False
    # k2 starts fresh.
    assert allow(lb, "k2", 0) is True


def test_rejects_empty_key() -> None:
    lb = LeakyBucket(capacity=5, rate_per_sec=1.0)
    with pytest.raises(ValueError, match="key"):
        allow(lb, "", 0)


def test_rejects_backwards_now() -> None:
    lb = LeakyBucket(capacity=5, rate_per_sec=1.0)
    allow(lb, "k1", 100)
    with pytest.raises(ValueError, match="earlier"):
        allow(lb, "k1", 50)


def test_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        LeakyBucket(capacity=0, rate_per_sec=1.0)


def test_invalid_rate() -> None:
    with pytest.raises(ValueError):
        LeakyBucket(capacity=10, rate_per_sec=0.0)


def test_long_run_admit_at_drain_rate() -> None:
    """At 5/s drain and 50/s incoming, long-run admit rate ≈ 10% + cap."""
    lb = LeakyBucket(capacity=5, rate_per_sec=5.0)
    admitted = sum(1 for i in range(1_000) if allow(lb, "k1", i * 20))
    # Initial 5 + 5/s × 20s ≈ 105 admits expected; allow ±20% slack.
    assert 90 <= admitted <= 140
