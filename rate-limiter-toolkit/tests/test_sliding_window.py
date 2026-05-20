"""Sliding-window-log tests."""

from __future__ import annotations

import pytest

from ratelimit.schema import SlidingWindowLog
from ratelimit.sliding_window import allow, current_count


def test_admits_up_to_capacity() -> None:
    sw = SlidingWindowLog(capacity=3, window_ms=1_000)
    assert allow(sw, "k1", 0) is True
    assert allow(sw, "k1", 100) is True
    assert allow(sw, "k1", 200) is True
    assert allow(sw, "k1", 300) is False


def test_evicts_old_entries() -> None:
    sw = SlidingWindowLog(capacity=3, window_ms=1_000)
    for ts in (0, 100, 200):
        allow(sw, "k1", ts)
    # At t=1001, the entry at t=0 falls outside the window.
    assert allow(sw, "k1", 1_001) is True


def test_per_key_isolation() -> None:
    sw = SlidingWindowLog(capacity=2, window_ms=500)
    for _ in range(2):
        allow(sw, "k1", 0)
    assert allow(sw, "k1", 0) is False
    # k2 starts fresh.
    assert allow(sw, "k2", 0) is True


def test_current_count() -> None:
    sw = SlidingWindowLog(capacity=5, window_ms=500)
    for ts in (0, 100, 200, 300):
        allow(sw, "k1", ts)
    assert current_count(sw, "k1", 400) == 4
    # Window slides past the first two entries.
    assert current_count(sw, "k1", 601) == 2


def test_rejects_empty_key() -> None:
    sw = SlidingWindowLog(capacity=3, window_ms=1_000)
    with pytest.raises(ValueError, match="key"):
        allow(sw, "", 0)


def test_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        SlidingWindowLog(capacity=0, window_ms=1_000)


def test_invalid_window() -> None:
    with pytest.raises(ValueError):
        SlidingWindowLog(capacity=10, window_ms=0)


def test_no_boundary_artifact() -> None:
    """Sliding window doesn't admit 2×capacity around a fixed-window boundary."""
    sw = SlidingWindowLog(capacity=5, window_ms=1_000)
    # 5 requests at t=999 fill the bucket; nothing in t=1000-1499 can pass.
    for _ in range(5):
        allow(sw, "k1", 999)
    # At t=1000 the t=999 entries are still in window. Should refuse.
    assert allow(sw, "k1", 1_000) is False


def test_long_idle_clears_log() -> None:
    sw = SlidingWindowLog(capacity=3, window_ms=1_000)
    for _ in range(3):
        allow(sw, "k1", 0)
    # Long idle clears the log.
    assert allow(sw, "k1", 10_000) is True
    assert current_count(sw, "k1", 10_000) == 1
