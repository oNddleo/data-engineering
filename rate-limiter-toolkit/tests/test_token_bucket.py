"""Tests for TokenBucket rate limiter."""

from __future__ import annotations

import pytest

from ratelimiter.token_bucket import RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class TestBasic:
    def test_starts_full(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=1.0, _clock=clock)
        assert tb.tokens == 10.0

    def test_acquire_reduces_tokens(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=1.0, _clock=clock)
        assert tb.acquire(3)
        assert abs(tb.tokens - 7.0) < 1e-9

    def test_acquire_fails_if_not_enough(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=5.0, refill_rate=1.0, _clock=clock)
        assert not tb.acquire(6)

    def test_acquire_or_raise_raises(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=3.0, refill_rate=1.0, _clock=clock)
        tb.acquire(3)
        with pytest.raises(RateLimitExceeded):
            tb.acquire_or_raise(1)

    def test_invalid_capacity_raises(self) -> None:
        with pytest.raises(ValueError):
            TokenBucket(capacity=0.0, refill_rate=1.0)

    def test_invalid_refill_rate_raises(self) -> None:
        with pytest.raises(ValueError):
            TokenBucket(capacity=1.0, refill_rate=0.0)

    def test_invalid_n_raises(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=1.0, _clock=clock)
        with pytest.raises(ValueError):
            tb.acquire(0)


class TestRefill:
    def test_refills_over_time(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=5.0, _clock=clock)
        tb.acquire(10)  # drain
        assert tb.tokens < 1.0
        clock.advance(1.0)  # +5 tokens
        assert abs(tb.tokens - 5.0) < 1e-6

    def test_refill_capped_at_capacity(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=5.0, _clock=clock)
        clock.advance(100.0)  # would add 500 tokens
        assert tb.tokens == 10.0

    def test_partial_refill(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=2.0, _clock=clock)
        tb.acquire(10)
        clock.advance(0.5)  # +1 token
        assert abs(tb.tokens - 1.0) < 1e-6


class TestTimeToTokens:
    def test_available_immediately(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=5.0, _clock=clock)
        assert tb.time_to_tokens(5) == 0.0

    def test_wait_time_calculation(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=5.0, _clock=clock)
        tb.acquire(10)  # drain
        wait = tb.time_to_tokens(5)
        assert abs(wait - 1.0) < 1e-6  # 5 tokens / 5 per sec = 1s


class TestSnapshot:
    def test_snapshot_keys(self) -> None:
        clock = FakeClock()
        tb = TokenBucket(capacity=10.0, refill_rate=2.0, name="api", _clock=clock)
        snap = tb.snapshot()
        assert snap["name"] == "api"
        assert snap["capacity"] == 10.0
        assert snap["refill_rate"] == 2.0
        assert "tokens" in snap
