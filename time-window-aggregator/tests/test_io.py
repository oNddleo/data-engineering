"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from windows.io_jsonl import (
    agg_from_dict,
    agg_to_dict,
    dump_aggs,
    dump_events,
    event_from_dict,
    event_to_dict,
    load_aggs,
    load_events,
    window_from_dict,
    window_to_dict,
)
from windows.schema import Event, Window, WindowedAggregate, WindowKind
from windows.tumbling import aggregate


def test_event_roundtrip() -> None:
    e = Event(key="k1", value=42, ts_ms=1_000)
    assert event_from_dict(event_to_dict(e)) == e


def test_window_roundtrip() -> None:
    w = Window(start_ms=0, end_ms=60_000, kind=WindowKind.TUMBLING)
    assert window_from_dict(window_to_dict(w)) == w


def test_agg_roundtrip() -> None:
    a = WindowedAggregate(
        window=Window(0, 1_000, WindowKind.SLIDING),
        key="k1",
        count=5,
        sum_value=500,
        min_value=10,
        max_value=200,
    )
    assert agg_from_dict(agg_to_dict(a)) == a


def test_dump_load_events_many() -> None:
    events = [Event(f"k{i}", i, i * 100) for i in range(1, 6)]
    assert load_events(dump_events(events)) == events


def test_dump_load_aggs_many() -> None:
    events = [Event("k1", i, i * 50) for i in range(1, 11)]
    aggs = aggregate(events, width_ms=100)
    assert load_aggs(dump_aggs(aggs)) == aggs


def test_dump_skips_blank_lines() -> None:
    events = [Event("k1", 1, 0)]
    text = "\n\n" + dump_events(events) + "\n\n"
    assert load_events(text) == events


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_events("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    bad = '{"key": 123, "value": 1, "ts_ms": 0}\n'
    with pytest.raises(TypeError, match="key"):
        load_events(bad)
