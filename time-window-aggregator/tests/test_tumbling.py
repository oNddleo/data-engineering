"""Tumbling-window aggregation."""

from __future__ import annotations

import pytest

from windows.schema import Event, WindowKind
from windows.tumbling import aggregate, assign_window


def test_assign_window_basic() -> None:
    """ts=150 with width=100 → [100, 200)."""
    w = assign_window(150, 100)
    assert w.start_ms == 100 and w.end_ms == 200


def test_assign_window_boundary() -> None:
    """ts=100 with width=100 lands in [100, 200), not [0, 100)."""
    w = assign_window(100, 100)
    assert w.start_ms == 100


def test_assign_window_zero() -> None:
    w = assign_window(0, 60_000)
    assert w.start_ms == 0


def test_assign_window_rejects_zero_width() -> None:
    with pytest.raises(ValueError, match="width_ms"):
        assign_window(100, 0)


def test_assign_window_rejects_negative_ts() -> None:
    with pytest.raises(ValueError, match="ts_ms"):
        assign_window(-1, 100)


def test_aggregate_single_window() -> None:
    events = [
        Event("k1", 10, 0),
        Event("k1", 20, 50),
        Event("k1", 30, 90),
    ]
    aggs = aggregate(events, width_ms=100)
    assert len(aggs) == 1
    a = aggs[0]
    assert a.count == 3
    assert a.sum_value == 60
    assert a.min_value == 10
    assert a.max_value == 30


def test_aggregate_multiple_windows() -> None:
    events = [
        Event("k1", 10, 0),
        Event("k1", 20, 100),  # next window
        Event("k1", 30, 250),  # third window
    ]
    aggs = aggregate(events, width_ms=100)
    assert len(aggs) == 3


def test_aggregate_per_key() -> None:
    """Events with different keys produce separate per-(window, key) rollups."""
    events = [
        Event("k1", 10, 0),
        Event("k2", 20, 50),
    ]
    aggs = aggregate(events, width_ms=100)
    assert len(aggs) == 2
    assert {a.key for a in aggs} == {"k1", "k2"}


def test_aggregate_sorted_by_window_then_key() -> None:
    events = [
        Event("k2", 5, 0),
        Event("k1", 10, 0),
    ]
    aggs = aggregate(events, width_ms=100)
    assert [a.key for a in aggs] == ["k1", "k2"]


def test_aggregate_empty() -> None:
    assert aggregate([], width_ms=100) == []


def test_aggregate_kind_is_tumbling() -> None:
    aggs = aggregate([Event("k", 1, 0)], width_ms=100)
    assert aggs[0].window.kind is WindowKind.TUMBLING


def test_aggregate_count_conservation() -> None:
    """Sum of per-window counts equals total event count."""
    events = [Event("k", 1, ts) for ts in range(0, 1000, 50)]
    aggs = aggregate(events, width_ms=200)
    assert sum(a.count for a in aggs) == len(events)
