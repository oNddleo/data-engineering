"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import timedelta

import pytest

from cartrec.attribute import AttributedTouch, AttributionVerdict
from cartrec.io_jsonl import (
    attributed_from_dict,
    dump_attributed,
    dump_events,
    dump_sessions,
    dump_touches,
    event_from_dict,
    load_attributed,
    load_events,
    load_sessions,
    load_touches,
    session_from_dict,
    touch_from_dict,
)
from cartrec.schema import CampaignTouch, TouchChannel
from cartrec.sessionize import sessionize

from ._fixtures import DEFAULT_TS, make_add, make_view


def test_event_roundtrip():
    e = make_view()
    [back] = list(load_events(dump_events([e])))
    assert back == e


def test_event_with_price_roundtrip():
    e = make_add()
    [back] = list(load_events(dump_events([e])))
    assert back == e


def test_session_roundtrip():
    sessions = sessionize([make_add(), make_view(t_min=1)])
    text = dump_sessions(sessions)
    back = list(load_sessions(text))
    assert back == sessions


def test_touch_roundtrip():
    t = CampaignTouch(
        touch_id="T-1",
        session_id="S-1",
        buyer_id="B-1",
        channel=TouchChannel.EMAIL,
        scheduled_at=DEFAULT_TS + timedelta(minutes=60),
        delay_minutes=60,
    )
    [back] = list(load_touches(dump_touches([t])))
    assert back == t


def test_attributed_roundtrip():
    t = CampaignTouch(
        touch_id="T-1",
        session_id="S-1",
        buyer_id="B-1",
        channel=TouchChannel.SMS,
        scheduled_at=DEFAULT_TS,
        delay_minutes=0,
    )
    at = AttributedTouch(
        touch=t,
        verdict=AttributionVerdict.CONVERTED,
        conversion_event_id="E-CONV",
    )
    [back] = list(load_attributed(dump_attributed([at])))
    assert back == at


def test_event_decoder_rejects_unknown_kind():
    bad = {
        "event_id": "E",
        "buyer_id": "B",
        "kind": "WEIRD",
        "occurred_at": "2026-05-01T09:00:00+07:00",
        "item_id": None,
        "unit_price_vnd": None,
    }
    with pytest.raises(ValueError):
        event_from_dict(bad)


def test_event_decoder_rejects_bool_for_int():
    """``bool`` is a subclass of ``int`` — must be rejected explicitly."""
    bad = {
        "event_id": "E",
        "buyer_id": "B",
        "kind": "ADD_TO_CART",
        "occurred_at": "2026-05-01T09:00:00+07:00",
        "item_id": "I",
        "unit_price_vnd": True,
    }
    with pytest.raises(TypeError, match="unit_price_vnd"):
        event_from_dict(bad)


def test_session_decoder_rejects_string_for_bool():
    bad = {
        "session_id": "S",
        "buyer_id": "B",
        "started_at": "2026-05-01T09:00:00+07:00",
        "ended_at": "2026-05-01T09:05:00+07:00",
        "n_events": 1,
        "n_views": 0,
        "n_add": 1,
        "n_remove": 0,
        "cart_value_vnd": 100,
        "distinct_items": 1,
        "started_checkout": "true",
        "completed_checkout": False,
        "explicit_abandon": False,
    }
    with pytest.raises(TypeError, match="started_checkout"):
        session_from_dict(bad)


def test_touch_decoder_rejects_unknown_channel():
    bad = {
        "touch_id": "T",
        "session_id": "S",
        "buyer_id": "B",
        "channel": "POSTCARD",
        "scheduled_at": "2026-05-01T09:00:00+07:00",
        "delay_minutes": 0,
    }
    with pytest.raises(ValueError):
        touch_from_dict(bad)


def test_attributed_decoder_rejects_non_object_touch():
    bad = {"touch": "not-an-object", "verdict": "CONVERTED", "conversion_event_id": None}
    with pytest.raises(TypeError, match="touch"):
        attributed_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_events([make_view()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_events(padded))) == 1


def test_multi_event_roundtrip():
    events = [make_view(t_min=i) for i in range(5)]
    text = dump_events(events)
    assert list(load_events(text)) == events
