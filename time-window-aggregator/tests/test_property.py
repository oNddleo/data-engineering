"""Hypothesis property tests for window invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from windows.io_jsonl import agg_from_dict, agg_to_dict, event_from_dict, event_to_dict
from windows.schema import Event
from windows.session import aggregate as session_agg
from windows.sliding import aggregate as sliding_agg
from windows.sliding import windows_for
from windows.tumbling import aggregate as tumbling_agg
from windows.tumbling import assign_window

_keys = st.sampled_from(["k1", "k2", "k3"])
_ts = st.integers(min_value=0, max_value=1_000_000)
_val = st.integers(min_value=-1000, max_value=1000)


@st.composite
def event(draw: st.DrawFn) -> Event:
    return Event(key=draw(_keys), value=draw(_val), ts_ms=draw(_ts))


# ---------- Tumbling invariants -------------------------------------------


@given(_ts, st.integers(min_value=1, max_value=10_000))
def test_assign_window_contains_ts(ts: int, width: int) -> None:
    w = assign_window(ts, width)
    assert w.contains(ts)


@given(_ts, st.integers(min_value=1, max_value=10_000))
def test_assign_window_aligned_to_width(ts: int, width: int) -> None:
    """Window starts are multiples of width."""
    w = assign_window(ts, width)
    assert w.start_ms % width == 0
    assert w.width_ms == width


@given(st.lists(event(), min_size=1, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_tumbling_count_conserves(events: list[Event]) -> None:
    """Sum of per-window counts == total events."""
    aggs = tumbling_agg(events, width_ms=1_000)
    assert sum(a.count for a in aggs) == len(events)


@given(st.lists(event(), min_size=1, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_tumbling_sum_conserves(events: list[Event]) -> None:
    """Sum of per-window sum_value == total event value."""
    aggs = tumbling_agg(events, width_ms=1_000)
    assert sum(a.sum_value for a in aggs) == sum(e.value for e in events)


# ---------- Sliding invariants --------------------------------------------


@given(
    _ts,
    st.integers(min_value=1, max_value=1_000),
    st.integers(min_value=1, max_value=1_000),
)
def test_sliding_windows_contain_ts(ts: int, width: int, stride: int) -> None:
    """Every returned window contains the event."""
    for w in windows_for(ts, width_ms=width, stride_ms=stride):
        assert w.contains(ts)


@given(
    _ts,
    st.integers(min_value=1, max_value=1_000),
    st.integers(min_value=1, max_value=1_000),
)
def test_sliding_windows_aligned_to_stride(
    ts: int,
    width: int,
    stride: int,
) -> None:
    """Every returned window starts at a multiple of stride."""
    for w in windows_for(ts, width_ms=width, stride_ms=stride):
        assert w.start_ms % stride == 0


@given(st.lists(event(), min_size=1, max_size=30))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_sliding_stride_eq_width_equals_tumbling(events: list[Event]) -> None:
    """When stride == width, sliding aggregation matches tumbling."""
    sliding = sliding_agg(events, width_ms=500, stride_ms=500)
    tumbling = tumbling_agg(events, width_ms=500)
    # Compare by (window, key) keys → counts must match.
    by_key_sliding = {(a.window.start_ms, a.key): a.count for a in sliding}
    by_key_tumbling = {(a.window.start_ms, a.key): a.count for a in tumbling}
    assert by_key_sliding == by_key_tumbling


# ---------- Session invariants --------------------------------------------


@given(st.lists(event(), min_size=1, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_session_count_conserves(events: list[Event]) -> None:
    """Sum of per-session counts == total events."""
    aggs = session_agg(events, timeout_ms=1_000)
    assert sum(a.count for a in aggs) == len(events)


@given(st.lists(event(), min_size=1, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_session_window_spans_session(events: list[Event]) -> None:
    """Every session window contains its first event ts."""
    aggs = session_agg(events, timeout_ms=10_000)
    for a in aggs:
        assert a.window.start_ms <= a.window.end_ms - 1


# ---------- JSONL round-trip ----------------------------------------------


@given(event())
def test_event_roundtrip(e: Event) -> None:
    assert event_from_dict(event_to_dict(e)) == e


@given(st.lists(event(), min_size=1, max_size=30))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_agg_jsonl_roundtrip(events: list[Event]) -> None:
    aggs = tumbling_agg(events, width_ms=500)
    for a in aggs:
        assert agg_from_dict(agg_to_dict(a)) == a
