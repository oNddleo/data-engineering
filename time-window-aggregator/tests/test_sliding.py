"""Sliding-window aggregation."""

from __future__ import annotations

import pytest

from windows.schema import Event, WindowKind
from windows.sliding import aggregate, windows_for


def test_windows_for_basic() -> None:
    """ts=150, width=100, stride=50 → windows [100,200) and [150,250)."""
    wins = windows_for(150, width_ms=100, stride_ms=50)
    starts = {w.start_ms for w in wins}
    # k=2 (start=100, end=200) contains 150; k=3 (start=150, end=250) too.
    assert 100 in starts
    assert 150 in starts


def test_windows_for_at_start() -> None:
    """ts=0 lands only in the [0, width) window."""
    wins = windows_for(0, width_ms=100, stride_ms=50)
    assert len(wins) == 1
    assert wins[0].start_ms == 0


def test_windows_for_stride_equals_width() -> None:
    """When stride == width, sliding reduces to tumbling — one window each."""
    wins = windows_for(150, width_ms=100, stride_ms=100)
    assert len(wins) == 1


def test_windows_for_rejects_zero_width() -> None:
    with pytest.raises(ValueError, match="width_ms"):
        windows_for(100, width_ms=0, stride_ms=50)


def test_windows_for_rejects_zero_stride() -> None:
    with pytest.raises(ValueError, match="stride_ms"):
        windows_for(100, width_ms=100, stride_ms=0)


def test_aggregate_overlapping_counts() -> None:
    """An event in overlap zone appears in multiple windows."""
    events = [Event("k1", 10, 75)]
    aggs = aggregate(events, width_ms=100, stride_ms=50)
    # ts=75: k=1 (50-150) and k=0 (0-100). Both contain 75.
    assert len(aggs) == 2


def test_aggregate_kind_is_sliding() -> None:
    aggs = aggregate([Event("k1", 10, 0)], width_ms=100, stride_ms=50)
    for a in aggs:
        assert a.window.kind is WindowKind.SLIDING


def test_aggregate_no_overlap_at_stride_eq_width() -> None:
    """stride == width → each event lands in one window."""
    events = [Event("k1", 1, ts) for ts in (0, 50, 100, 150, 200)]
    aggs = aggregate(events, width_ms=100, stride_ms=100)
    # 0..50 → win [0, 100); 100..150 → win [100, 200); 200 → win [200, 300).
    assert len(aggs) == 3


def test_aggregate_count_multiplied_by_overlap() -> None:
    """When stride < width, total agg count > total event count."""
    events = [Event("k1", 1, ts) for ts in range(0, 200, 10)]
    aggs = aggregate(events, width_ms=100, stride_ms=50)
    total_agg_count = sum(a.count for a in aggs)
    assert total_agg_count > len(events)


def test_aggregate_empty() -> None:
    assert aggregate([], width_ms=100, stride_ms=50) == []
