"""Conversion attribution."""

from __future__ import annotations

from datetime import timedelta

import pytest

from cartrec.attribute import (
    AttributionVerdict,
    attribute,
    conversion_by_channel,
    conversion_rate,
)
from cartrec.schema import CampaignTouch, EventKind, TouchChannel

from ._fixtures import DEFAULT_TS, make_add, make_event


def _touch(buyer_id: str, channel: TouchChannel, t_min: int) -> CampaignTouch:
    return CampaignTouch(
        touch_id=f"T-{buyer_id}-{channel.value}",
        session_id=f"S-{buyer_id}",
        buyer_id=buyer_id,
        channel=channel,
        scheduled_at=DEFAULT_TS + timedelta(minutes=t_min),
        delay_minutes=t_min,
    )


def test_no_touches_no_attributions():
    assert attribute([], []) == []


def test_conversion_within_window_credits_touch():
    t = _touch("B-1", TouchChannel.EMAIL, 60)
    # Conversion 2h after touch — within 24h window.
    conv = make_event(
        event_id="E-CONV",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t], [conv], attribution_window_hours=24)
    assert len(result) == 1
    assert result[0].verdict is AttributionVerdict.CONVERTED
    assert result[0].conversion_event_id == "E-CONV"


def test_conversion_outside_window_not_credited():
    t = _touch("B-1", TouchChannel.EMAIL, 60)
    # Conversion 48h after touch — outside 24h window.
    conv = make_event(
        event_id="E-LATE",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=49),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t], [conv], attribution_window_hours=24)
    assert result[0].verdict is AttributionVerdict.NOT_CONVERTED


def test_conversion_before_touch_ignored():
    """A conversion *before* the touch fired is not eligible."""
    t = _touch("B-1", TouchChannel.EMAIL, 60)
    # Pre-touch conversion (the buyer bought before the email even arrived).
    conv = make_event(
        event_id="E-PRE",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(minutes=30),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t], [conv])
    assert result[0].verdict is AttributionVerdict.NOT_CONVERTED


def test_non_complete_events_ignored():
    """Only ``COMPLETE_CHECKOUT`` events qualify as conversions."""
    t = _touch("B-1", TouchChannel.EMAIL, 60)
    views = [make_add(buyer_id="B-1", t_min=120)]  # not a checkout completion
    result = attribute([t], views)
    assert result[0].verdict is AttributionVerdict.NOT_CONVERTED


def test_first_touch_attribution_default():
    """When two touches fall before the conversion, the first wins (default)."""
    t1 = _touch("B-1", TouchChannel.EMAIL, 60)
    t2 = _touch("B-1", TouchChannel.SMS, 24 * 60)
    # Conversion 25h after session — within EMAIL window AND SMS window.
    conv = make_event(
        event_id="E-CONV",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=25),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t1, t2], [conv], attribution_window_hours=24)
    # EMAIL gets credit (first touch within window).
    by_id = {a.touch.touch_id: a for a in result}
    assert by_id[t1.touch_id].verdict is AttributionVerdict.CONVERTED
    assert by_id[t2.touch_id].verdict is AttributionVerdict.NOT_CONVERTED


def test_last_touch_attribution():
    """``last_touch=True`` flips credit to the more-recent touch."""
    t1 = _touch("B-1", TouchChannel.EMAIL, 60)
    t2 = _touch("B-1", TouchChannel.SMS, 24 * 60)
    conv = make_event(
        event_id="E-CONV",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=25),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t1, t2], [conv], attribution_window_hours=24, last_touch=True)
    by_id = {a.touch.touch_id: a for a in result}
    assert by_id[t2.touch_id].verdict is AttributionVerdict.CONVERTED
    assert by_id[t1.touch_id].verdict is AttributionVerdict.NOT_CONVERTED


def test_independent_per_buyer():
    """B-1's conversion doesn't credit B-2's touch."""
    t1 = _touch("B-1", TouchChannel.EMAIL, 60)
    t2 = _touch("B-2", TouchChannel.EMAIL, 60)
    conv = make_event(
        event_id="E-CONV",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t1, t2], [conv])
    by_id = {a.touch.touch_id: a for a in result}
    assert by_id[t1.touch_id].verdict is AttributionVerdict.CONVERTED
    assert by_id[t2.touch_id].verdict is AttributionVerdict.NOT_CONVERTED


def test_one_conversion_credits_one_touch():
    """Two completions credit at most two touches, not one touch twice."""
    t1 = _touch("B-1", TouchChannel.EMAIL, 60)
    t2 = _touch("B-2", TouchChannel.EMAIL, 60)
    # One conversion per buyer.
    conv1 = make_event(
        event_id="E-1",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    conv2 = make_event(
        event_id="E-2",
        buyer_id="B-2",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t1, t2], [conv1, conv2])
    assert sum(1 for a in result if a.verdict is AttributionVerdict.CONVERTED) == 2


def test_conversion_rate():
    """``conversion_rate`` returns converted ÷ total."""
    t = _touch("B-1", TouchChannel.EMAIL, 60)
    conv = make_event(
        event_id="E",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t], [conv])
    assert conversion_rate(result) == 1.0


def test_conversion_rate_empty_input():
    assert conversion_rate([]) == 0.0


def test_conversion_by_channel():
    """Per-channel breakdown."""
    t_email = _touch("B-1", TouchChannel.EMAIL, 60)
    t_sms = _touch("B-2", TouchChannel.SMS, 24 * 60)
    conv = make_event(
        event_id="E",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=DEFAULT_TS + timedelta(hours=3),
        item_id=None,
        unit_price_vnd=None,
    )
    result = attribute([t_email, t_sms], [conv])
    by_ch = conversion_by_channel(result)
    assert by_ch["EMAIL"] == 1.0
    assert by_ch["SMS"] == 0.0


def test_validates_window():
    with pytest.raises(ValueError):
        attribute([], [], attribution_window_hours=0)
