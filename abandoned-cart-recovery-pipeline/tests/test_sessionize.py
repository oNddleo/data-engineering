"""Sessionizer behaviour."""

from __future__ import annotations

import pytest

from cartrec.sessionize import sessionize

from ._fixtures import make_add, make_checkout, make_remove, make_view


def test_single_event_single_session():
    sessions = sessionize([make_view()])
    assert len(sessions) == 1
    assert sessions[0].n_events == 1


def test_events_within_window_single_session():
    """All events within idle gap → one session."""
    events = [make_view(t_min=0), make_add(t_min=5), make_view(t_min=10)]
    sessions = sessionize(events, idle_gap_minutes=30)
    assert len(sessions) == 1
    assert sessions[0].n_events == 3


def test_events_beyond_gap_split_into_sessions():
    """A 90-min idle gap splits into two sessions."""
    events = [make_view(t_min=0), make_add(t_min=5), make_view(t_min=120)]  # 115 min after last
    sessions = sessionize(events, idle_gap_minutes=30)
    assert len(sessions) == 2


def test_complete_checkout_forces_session_boundary():
    """An event right after COMPLETE_CHECKOUT opens a new session
    even if it's within the idle gap."""
    events = [
        make_add(t_min=0),
        make_checkout(t_min=5, complete=True),
        make_view(t_min=10),  # within 5-min gap, but checkout closed the session
    ]
    sessions = sessionize(events, idle_gap_minutes=30)
    assert len(sessions) == 2
    assert sessions[0].completed_checkout
    assert not sessions[1].completed_checkout


def test_abandon_checkout_also_forces_boundary():
    events = [
        make_add(t_min=0),
        make_checkout(t_min=5, complete=False),  # ABANDON
        make_view(t_min=10),
    ]
    sessions = sessionize(events, idle_gap_minutes=30)
    assert len(sessions) == 2
    assert sessions[0].explicit_abandon
    assert not sessions[1].explicit_abandon


def test_cart_value_tracks_add_remove_net():
    events = [
        make_add(t_min=0, price=100_000),
        make_add(t_min=1, item="ITEM-2", price=200_000),
        make_remove(t_min=2, price=100_000),  # removes ITEM-1
    ]
    sessions = sessionize(events)
    assert sessions[0].cart_value_vnd == 200_000
    assert sessions[0].n_add == 2
    assert sessions[0].n_remove == 1
    assert sessions[0].distinct_items == 1  # ITEM-2 remains


def test_cart_value_clamped_at_zero():
    """Out-of-order webhook with REMOVE before ADD → cart_value clamped to 0."""
    events = [
        make_remove(t_min=0, price=100_000),
        make_add(t_min=1, price=50_000),
    ]
    sessions = sessionize(events)
    # Net would be 50_000 - 100_000 = -50_000; clamp to 0.
    assert sessions[0].cart_value_vnd == 0


def test_out_of_order_events_resorted():
    """Events arriving in shuffled order are re-sorted per buyer."""
    events = [
        make_view(t_min=10),
        make_add(t_min=5),
        make_view(t_min=0),
    ]
    sessions = sessionize(events)
    assert len(sessions) == 1
    assert sessions[0].n_views == 2
    assert sessions[0].n_add == 1


def test_multiple_buyers_independent_sessions():
    events = [
        make_view(buyer_id="B-1", t_min=0),
        make_add(buyer_id="B-1", t_min=1),
        make_view(buyer_id="B-2", t_min=0),
        make_add(buyer_id="B-2", t_min=1),
    ]
    sessions = sessionize(events)
    assert len(sessions) == 2
    assert {s.buyer_id for s in sessions} == {"B-1", "B-2"}


def test_output_sorted_by_buyer_then_start():
    events = [
        make_view(buyer_id="B-B", t_min=0),
        make_view(buyer_id="B-A", t_min=0),
    ]
    sessions = sessionize(events)
    assert [s.buyer_id for s in sessions] == ["B-A", "B-B"]


def test_validates_idle_gap():
    with pytest.raises(ValueError):
        sessionize([], idle_gap_minutes=0)
    with pytest.raises(ValueError):
        sessionize([], idle_gap_minutes=-1)


def test_complete_checkout_session_has_no_explicit_abandon():
    """Session that completed shouldn't also be flagged explicit_abandon."""
    events = [make_add(t_min=0), make_checkout(t_min=5, complete=True)]
    sessions = sessionize(events)
    assert sessions[0].completed_checkout
    assert not sessions[0].explicit_abandon


def test_empty_input():
    assert sessionize([]) == []
