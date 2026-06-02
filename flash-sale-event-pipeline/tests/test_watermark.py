"""Watermark tracker tests."""

from __future__ import annotations

import pytest

from flashpipe.watermark import WatermarkTracker

from ._fixtures import t_at


def test_initial_watermark_is_none():
    w = WatermarkTracker()
    assert w.watermark is None


def test_observe_advances_watermark():
    w = WatermarkTracker(max_out_of_orderness_seconds=2.0)
    w.observe(t_at(10))
    assert w.watermark == t_at(8)


def test_watermark_monotonic_on_later_event():
    w = WatermarkTracker(max_out_of_orderness_seconds=2.0)
    w.observe(t_at(10))
    w.observe(t_at(20))
    assert w.watermark == t_at(18)


def test_watermark_does_not_regress_on_earlier_event():
    w = WatermarkTracker(max_out_of_orderness_seconds=2.0)
    w.observe(t_at(20))
    w.observe(t_at(10))  # late event
    assert w.watermark == t_at(18)  # unchanged


def test_is_late_returns_false_before_any_events():
    w = WatermarkTracker()
    assert not w.is_late(t_at(0))


def test_is_late_detects_event_before_watermark():
    w = WatermarkTracker(max_out_of_orderness_seconds=2.0)
    w.observe(t_at(100))
    assert w.is_late(t_at(97))


def test_is_late_returns_false_for_event_at_watermark():
    """``event_time < watermark`` — equal is NOT late."""
    w = WatermarkTracker(max_out_of_orderness_seconds=2.0)
    w.observe(t_at(100))
    assert not w.is_late(t_at(98))  # equal to watermark


def test_rejects_negative_max_out_of_orderness():
    with pytest.raises(ValueError):
        WatermarkTracker(max_out_of_orderness_seconds=-1)


def test_zero_max_out_of_orderness_equals_event_time():
    w = WatermarkTracker(max_out_of_orderness_seconds=0)
    w.observe(t_at(10))
    assert w.watermark == t_at(10)
