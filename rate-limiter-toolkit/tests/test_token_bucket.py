"""Token bucket tests."""

from __future__ import annotations

import pytest

from ratelimit.schema import TokenBucket
from ratelimit.token_bucket import allow, remaining


def test_initial_capacity_full() -> None:
    """A fresh bucket starts at full capacity."""
    tb = TokenBucket(capacity=10, rate_per_sec=1.0)
    assert remaining(tb, "k1", 0) == 10.0


def test_consume_one_token() -> None:
    tb = TokenBucket(capacity=5, rate_per_sec=1.0)
    assert allow(tb, "k1", 0) is True
    assert remaining(tb, "k1", 0) == 4.0


def test_throttles_when_empty() -> None:
    """Once the bucket is empty, further requests at t=0 are denied."""
    tb = TokenBucket(capacity=2, rate_per_sec=1.0)
    assert allow(tb, "k1", 0) is True
    assert allow(tb, "k1", 0) is True
    assert allow(tb, "k1", 0) is False


def test_refill_over_time() -> None:
    """After 1 second at 1/s rate, 1 token is restored."""
    tb = TokenBucket(capacity=5, rate_per_sec=1.0)
    for _ in range(5):
        allow(tb, "k1", 0)
    assert allow(tb, "k1", 0) is False
    # 1 full second passes → 1 token restored.
    assert allow(tb, "k1", 1_000) is True


def test_refill_caps_at_capacity() -> None:
    """Long idle period doesn't exceed capacity."""
    tb = TokenBucket(capacity=5, rate_per_sec=10.0)
    # Wait 10 seconds → would refill 100 tokens, but cap is 5.
    for _ in range(5):
        assert allow(tb, "k1", 10_000) is True
    assert allow(tb, "k1", 10_000) is False


def test_per_key_isolation() -> None:
    """Two keys have independent buckets."""
    tb = TokenBucket(capacity=2, rate_per_sec=1.0)
    assert allow(tb, "k1", 0) is True
    assert allow(tb, "k1", 0) is True
    assert allow(tb, "k1", 0) is False
    # k2 should still be at full capacity.
    assert allow(tb, "k2", 0) is True


def test_rejects_negative_now() -> None:
    tb = TokenBucket(capacity=2, rate_per_sec=1.0)
    with pytest.raises(ValueError, match="now_ms"):
        allow(tb, "k1", -1)


def test_rejects_backwards_now() -> None:
    """now_ms must be monotonic per key."""
    tb = TokenBucket(capacity=5, rate_per_sec=1.0)
    allow(tb, "k1", 100)
    with pytest.raises(ValueError, match="earlier"):
        allow(tb, "k1", 50)


def test_rejects_empty_key() -> None:
    tb = TokenBucket(capacity=5, rate_per_sec=1.0)
    with pytest.raises(ValueError, match="key"):
        allow(tb, "", 0)


def test_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        TokenBucket(capacity=0, rate_per_sec=1.0)


def test_invalid_rate() -> None:
    with pytest.raises(ValueError):
        TokenBucket(capacity=10, rate_per_sec=0.0)


def test_long_run_admit_rate() -> None:
    """At 10/s rate and 100/s incoming, long-run admit rate ≈ 10%."""
    tb = TokenBucket(capacity=10, rate_per_sec=10.0)
    admitted = sum(1 for i in range(1_000) if allow(tb, "k1", i * 10))
    # 10 burst + 10/s × 10s = 110 admits expected; allow ±20% slack.
    assert 80 <= admitted <= 140
