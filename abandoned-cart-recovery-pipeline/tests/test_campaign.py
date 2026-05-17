"""Campaign scheduler."""

from __future__ import annotations

from datetime import timedelta

import pytest

from cartrec.campaign import DEFAULT_CADENCE, filter_due, schedule
from cartrec.detect import find_abandoned
from cartrec.schema import TouchChannel
from cartrec.sessionize import sessionize

from ._fixtures import make_add


def _abandoned():  # type: ignore[no-untyped-def]
    events = [make_add(price=200_000)]
    sessions = sessionize(events)
    return find_abandoned(sessions)


def test_default_cadence_three_touches():
    abandoned = _abandoned()
    touches = schedule(abandoned)
    assert len(touches) == 3
    assert [t.channel for t in touches] == [
        TouchChannel.EMAIL,
        TouchChannel.SMS,
        TouchChannel.PUSH,
    ]


def test_default_cadence_delays():
    abandoned = _abandoned()
    touches = schedule(abandoned)
    assert touches[0].delay_minutes == 60
    assert touches[1].delay_minutes == 24 * 60
    assert touches[2].delay_minutes == 72 * 60


def test_scheduled_at_offsets_from_session_end():
    abandoned = _abandoned()
    touches = schedule(abandoned)
    session_end = abandoned[0].session.ended_at
    assert touches[0].scheduled_at == session_end + timedelta(minutes=60)


def test_each_abandoned_session_gets_full_cadence():
    """N abandoned sessions × 3 default touches = 3N touches."""
    events = []
    for i in range(5):
        events.append(make_add(buyer_id=f"B-{i}", t_min=i * 100, price=200_000))
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions)
    touches = schedule(abandoned)
    assert len(touches) == len(abandoned) * len(DEFAULT_CADENCE)


def test_custom_cadence():
    abandoned = _abandoned()
    touches = schedule(abandoned, cadence=((30, TouchChannel.PUSH),))
    assert len(touches) == 1
    assert touches[0].channel is TouchChannel.PUSH
    assert touches[0].delay_minutes == 30


def test_schedule_validates_empty_cadence():
    with pytest.raises(ValueError):
        schedule([], cadence=())


def test_schedule_validates_negative_delay():
    with pytest.raises(ValueError):
        schedule([], cadence=((-1, TouchChannel.EMAIL),))


def test_filter_due_returns_only_past_touches():
    abandoned = _abandoned()
    touches = schedule(abandoned)
    # ``now`` is 2h after session ended — only EMAIL (60min) is due.
    now = abandoned[0].session.ended_at + timedelta(hours=2)
    due = filter_due(touches, now)
    assert len(due) == 1
    assert due[0].channel is TouchChannel.EMAIL


def test_filter_due_requires_tz_aware():
    from datetime import datetime

    with pytest.raises(ValueError):
        filter_due([], datetime(2026, 5, 1))


def test_filter_due_requires_datetime():
    with pytest.raises(TypeError):
        filter_due([], "2026-05-01")


def test_filter_due_includes_equal_timestamps():
    abandoned = _abandoned()
    touches = schedule(abandoned)
    now = touches[0].scheduled_at  # exactly equal
    assert len(filter_due(touches, now)) == 1
