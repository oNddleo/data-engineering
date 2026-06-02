"""Hypothesis properties — invariants over the four pipeline stages."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from cartrec.attribute import AttributionVerdict, attribute
from cartrec.detect import abandon_rate, find_abandoned
from cartrec.schema import CampaignTouch, Event, EventKind, TouchChannel
from cartrec.sessionize import sessionize

from ._fixtures import DEFAULT_TS, make_event


@st.composite
def _events_one_buyer(draw: st.DrawFn) -> list[Event]:
    """Random funnel-event sequence for one buyer (in chronological order)."""
    n = draw(st.integers(min_value=1, max_value=15))
    kinds = draw(
        st.lists(
            st.sampled_from(
                [
                    EventKind.VIEW_ITEM,
                    EventKind.ADD_TO_CART,
                    EventKind.START_CHECKOUT,
                    EventKind.COMPLETE_CHECKOUT,
                ]
            ),
            min_size=n,
            max_size=n,
        )
    )
    out: list[Event] = []
    for i, kind in enumerate(kinds):
        item_id = "ITEM-1" if kind in (EventKind.ADD_TO_CART, EventKind.REMOVE_FROM_CART) else None
        unit_price = (
            100_000 if kind in (EventKind.ADD_TO_CART, EventKind.REMOVE_FROM_CART) else None
        )
        out.append(
            make_event(
                event_id=f"E-{i:04d}",
                buyer_id="B-1",
                kind=kind,
                occurred_at=DEFAULT_TS + timedelta(minutes=i * 5),
                item_id=item_id,
                unit_price_vnd=unit_price,
            )
        )
    return out


@given(events=_events_one_buyer())
@settings(max_examples=50)
def test_session_event_count_matches_input(events: list[Event]) -> None:
    """Sum of ``n_events`` across sessions equals input length."""
    sessions = sessionize(events)
    assert sum(s.n_events for s in sessions) == len(events)


@given(events=_events_one_buyer())
@settings(max_examples=50)
def test_session_started_at_le_ended_at(events: list[Event]) -> None:
    """``started_at <= ended_at`` for every session."""
    sessions = sessionize(events)
    for s in sessions:
        assert s.started_at <= s.ended_at


@given(events=_events_one_buyer())
@settings(max_examples=50)
def test_cart_value_non_negative(events: list[Event]) -> None:
    """Cart value is always >= 0 (remove-without-add doesn't go negative)."""
    sessions = sessionize(events)
    assert all(s.cart_value_vnd >= 0 for s in sessions)


@given(events=_events_one_buyer())
@settings(max_examples=50)
def test_abandon_rate_in_unit_interval(events: list[Event]) -> None:
    """abandon_rate is always in [0, 1] regardless of input."""
    sessions = sessionize(events)
    r = abandon_rate(sessions)
    assert 0.0 <= r <= 1.0


@given(events=_events_one_buyer())
@settings(max_examples=50)
def test_abandoned_sessions_subset_of_carting(events: list[Event]) -> None:
    """Every abandoned session has n_add >= 1 (was a carting session)."""
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions, min_cart_vnd=0)
    assert all(ab.session.n_add >= 1 for ab in abandoned)


@given(
    delay_min=st.integers(min_value=1, max_value=72 * 60),
    window_h=st.integers(min_value=1, max_value=72),
    conv_offset_h=st.integers(min_value=-2, max_value=80),
)
@settings(max_examples=100)
def test_attribution_consistent_with_window(
    delay_min: int,
    window_h: int,
    conv_offset_h: int,
) -> None:
    """A conversion is credited iff it falls in ``[touch_ts, touch_ts + window]``."""
    t = CampaignTouch(
        touch_id="T-1",
        session_id="S-1",
        buyer_id="B-1",
        channel=TouchChannel.EMAIL,
        scheduled_at=DEFAULT_TS + timedelta(minutes=delay_min),
        delay_minutes=delay_min,
    )
    conv_ts = t.scheduled_at + timedelta(hours=conv_offset_h)
    conv = make_event(
        event_id="E-C",
        buyer_id="B-1",
        kind=EventKind.COMPLETE_CHECKOUT,
        occurred_at=conv_ts,
        item_id=None,
        unit_price_vnd=None,
    )
    [result] = attribute([t], [conv], attribution_window_hours=window_h)
    in_window = 0 <= conv_offset_h <= window_h
    if in_window:
        assert result.verdict is AttributionVerdict.CONVERTED
    else:
        assert result.verdict is AttributionVerdict.NOT_CONVERTED
