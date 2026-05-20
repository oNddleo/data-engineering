"""Schema invariants for Window, Event, WindowedAggregate."""

from __future__ import annotations

import pytest

from windows.schema import Event, Window, WindowedAggregate, WindowKind


def test_window_basic() -> None:
    w = Window(start_ms=0, end_ms=60_000, kind=WindowKind.TUMBLING)
    assert w.width_ms == 60_000
    assert w.contains(30_000)
    assert not w.contains(60_000)  # half-open


def test_window_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="end_ms"):
        Window(start_ms=100, end_ms=50, kind=WindowKind.TUMBLING)


def test_window_rejects_zero_width() -> None:
    with pytest.raises(ValueError, match="end_ms"):
        Window(start_ms=100, end_ms=100, kind=WindowKind.TUMBLING)


def test_window_rejects_negative_start() -> None:
    with pytest.raises(ValueError, match="start_ms"):
        Window(start_ms=-1, end_ms=100, kind=WindowKind.TUMBLING)


def test_window_contains_half_open() -> None:
    w = Window(start_ms=10, end_ms=20, kind=WindowKind.TUMBLING)
    assert w.contains(10) is True  # inclusive start
    assert w.contains(15) is True
    assert w.contains(20) is False  # exclusive end
    assert w.contains(9) is False


def test_event_basic() -> None:
    e = Event(key="k1", value=42, ts_ms=1_000)
    assert e.value == 42


def test_event_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="key"):
        Event(key="", value=1, ts_ms=0)


def test_event_rejects_negative_ts() -> None:
    with pytest.raises(ValueError, match="ts_ms"):
        Event(key="k", value=1, ts_ms=-1)


def test_window_kinds_complete() -> None:
    assert {k.value for k in WindowKind} == {"TUMBLING", "SLIDING", "SESSION"}


def test_agg_basic() -> None:
    a = WindowedAggregate(
        window=Window(0, 1_000, WindowKind.TUMBLING),
        key="k1",
        count=5,
        sum_value=500,
        min_value=50,
        max_value=200,
    )
    assert a.avg_value == 100.0


def test_agg_rejects_min_above_max() -> None:
    with pytest.raises(ValueError, match="min_value"):
        WindowedAggregate(
            window=Window(0, 1_000, WindowKind.TUMBLING),
            key="k1",
            count=1,
            sum_value=10,
            min_value=200,
            max_value=100,
        )


def test_agg_empty_zero_avg() -> None:
    """count=0 → avg=0.0, no ZeroDivisionError."""
    a = WindowedAggregate(
        window=Window(0, 1_000, WindowKind.TUMBLING),
        key="k1",
        count=0,
        sum_value=0,
        min_value=0,
        max_value=0,
    )
    assert a.avg_value == 0.0


def test_agg_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="count"):
        WindowedAggregate(
            window=Window(0, 1_000, WindowKind.TUMBLING),
            key="k",
            count=-1,
            sum_value=0,
            min_value=0,
            max_value=0,
        )
