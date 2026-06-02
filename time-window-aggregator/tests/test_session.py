"""Session-window aggregation."""

from __future__ import annotations

import pytest

from windows.schema import Event, WindowKind
from windows.session import aggregate


def test_aggregate_single_session() -> None:
    """Events within timeout collapse to one session."""
    events = [Event("k1", 1, ts) for ts in (0, 100, 200, 300)]
    aggs = aggregate(events, timeout_ms=500)
    assert len(aggs) == 1
    assert aggs[0].count == 4


def test_aggregate_two_sessions_split_by_gap() -> None:
    """A gap > timeout opens a new session."""
    events = [
        Event("k1", 1, 0),
        Event("k1", 1, 100),
        Event("k1", 1, 5_000),
        Event("k1", 1, 5_100),
    ]
    aggs = aggregate(events, timeout_ms=1_000)
    assert len(aggs) == 2


def test_aggregate_per_key_sessions() -> None:
    """Sessions for different keys are independent."""
    events = [
        Event("k1", 1, 0),
        Event("k1", 1, 100),
        Event("k2", 1, 0),
        Event("k2", 1, 100),
    ]
    aggs = aggregate(events, timeout_ms=500)
    assert len(aggs) == 2
    assert {a.key for a in aggs} == {"k1", "k2"}


def test_aggregate_single_event_session() -> None:
    """A solitary event is its own session."""
    aggs = aggregate([Event("k1", 42, 1_000)], timeout_ms=500)
    assert len(aggs) == 1
    assert aggs[0].count == 1


def test_aggregate_kind_is_session() -> None:
    aggs = aggregate([Event("k1", 1, 100)], timeout_ms=500)
    assert aggs[0].window.kind is WindowKind.SESSION


def test_aggregate_window_spans_events() -> None:
    events = [Event("k1", 1, 100), Event("k1", 1, 200), Event("k1", 1, 300)]
    aggs = aggregate(events, timeout_ms=500)
    assert aggs[0].window.start_ms == 100
    # End is exclusive; the last event must lie inside, so end = last_ts + 1.
    assert aggs[0].window.end_ms == 301


def test_aggregate_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_ms"):
        aggregate([], timeout_ms=0)


def test_aggregate_empty() -> None:
    assert aggregate([], timeout_ms=500) == []


def test_aggregate_handles_unsorted_events() -> None:
    """Events arriving out of order are sorted internally per key."""
    events = [Event("k1", 1, 300), Event("k1", 1, 100), Event("k1", 1, 200)]
    aggs = aggregate(events, timeout_ms=500)
    assert len(aggs) == 1
    assert aggs[0].window.start_ms == 100


def test_aggregate_count_conservation() -> None:
    """Sum of per-session counts equals total event count."""
    events = [Event("k1", 1, ts) for ts in range(0, 100, 5)]
    events.extend(Event("k1", 1, ts) for ts in range(10_000, 10_050, 5))
    aggs = aggregate(events, timeout_ms=200)
    assert sum(a.count for a in aggs) == len(events)
