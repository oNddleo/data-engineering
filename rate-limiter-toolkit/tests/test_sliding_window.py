"""Tests for SlidingWindowCounter rate limiter."""

from __future__ import annotations

import pytest

from ratelimiter.sliding_window import SlidingWindowCounter
from ratelimiter.token_bucket import RateLimitExceeded


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class TestBasic:
    def test_starts_empty(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=5, window_s=1.0, _clock=clock)
        assert sw.current_count == 0

    def test_acquire_increments_count(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=5, window_s=1.0, _clock=clock)
        sw.acquire()
        sw.acquire()
        assert sw.current_count == 2

    def test_acquire_fails_at_limit(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=3, window_s=1.0, _clock=clock)
        for _ in range(3):
            assert sw.acquire()
        assert not sw.acquire()

    def test_acquire_or_raise_raises(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=2, window_s=1.0, _clock=clock)
        sw.acquire()
        sw.acquire()
        with pytest.raises(RateLimitExceeded):
            sw.acquire_or_raise()

    def test_invalid_limit_raises(self) -> None:
        with pytest.raises(ValueError):
            SlidingWindowCounter(limit=0, window_s=1.0)

    def test_invalid_window_raises(self) -> None:
        with pytest.raises(ValueError):
            SlidingWindowCounter(limit=5, window_s=0.0)


class TestEviction:
    def test_old_events_evicted(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=5, window_s=1.0, _clock=clock)
        for _ in range(5):
            sw.acquire()
        assert sw.current_count == 5
        clock.advance(1.01)  # window expired
        assert sw.current_count == 0
        assert sw.acquire()  # now allowed

    def test_partial_eviction(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=5, window_s=1.0, _clock=clock)
        sw.acquire()  # t=0
        clock.advance(0.5)
        sw.acquire()  # t=0.5
        clock.advance(0.6)  # t=1.1 → first event (t=0) evicted
        assert sw.current_count == 1

    def test_allows_again_after_window(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=3, window_s=1.0, _clock=clock)
        for _ in range(3):
            sw.acquire()
        assert not sw.acquire()
        clock.advance(1.01)
        assert sw.acquire()  # slot freed


class TestTimeToNextSlot:
    def test_slot_available_immediately(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=5, window_s=1.0, _clock=clock)
        assert sw.time_to_next_slot() == 0.0

    def test_wait_when_at_limit(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=1, window_s=1.0, _clock=clock)
        sw.acquire()  # fills at t=0
        clock.advance(0.3)
        wait = sw.time_to_next_slot()
        # oldest at t=0, window=1s → slot frees at t=1 → wait = 0.7
        assert abs(wait - 0.7) < 1e-6


class TestSnapshot:
    def test_snapshot_keys(self) -> None:
        clock = FakeClock()
        sw = SlidingWindowCounter(limit=10, window_s=60.0, name="api", _clock=clock)
        snap = sw.snapshot()
        assert snap["name"] == "api"
        assert snap["limit"] == 10
        assert snap["window_s"] == 60.0
        assert snap["current_count"] == 0
