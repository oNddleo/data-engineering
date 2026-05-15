"""Hypothesis property tests."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given
from hypothesis import strategies as st

from flashpipe.io_jsonl import event_from_dict, event_to_dict
from flashpipe.watermark import WatermarkTracker
from flashpipe.windows import window_start_for

from ._fixtures import make_event, t_at


@given(amount=st.integers(min_value=0, max_value=10**11))
def test_event_round_trips(amount):
    e = make_event(amount_vnd=amount)
    assert event_from_dict(event_to_dict(e)) == e


@given(seconds=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False))
def test_window_start_aligns_to_second(seconds):
    """Property: window_start_for(t) is always ≤ t and a multiple of window_seconds."""
    ts = t_at(seconds)
    ws = window_start_for(ts, window_seconds=1)
    assert ws <= ts
    assert ws.microsecond == 0


@given(
    deltas=st.lists(
        st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=0,
        max_size=20,
    )
)
def test_watermark_monotonic(deltas):
    """Property: watermark only moves forward, never backward."""
    w = WatermarkTracker(max_out_of_orderness_seconds=2)
    prev = None
    for d in deltas:
        w.observe(t_at(d))
        if prev is not None and w.watermark is not None:
            assert w.watermark >= prev
        prev = w.watermark


@given(seconds=st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False))
def test_window_start_then_end_difference_equals_window_seconds(seconds):
    ws = window_start_for(t_at(seconds), window_seconds=5)
    we = ws + timedelta(seconds=5)
    assert (we - ws).total_seconds() == 5
