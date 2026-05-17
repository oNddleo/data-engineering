"""Abandoned-session detection."""

from __future__ import annotations

import pytest

from cartrec.detect import AbandonReason, abandon_rate, find_abandoned
from cartrec.sessionize import sessionize

from ._fixtures import make_add, make_checkout, make_view


def test_completed_session_not_flagged():
    events = [make_add(t_min=0, price=100_000), make_checkout(t_min=5, complete=True)]
    sessions = sessionize(events)
    assert find_abandoned(sessions) == []


def test_pure_browse_session_not_flagged():
    """A session with VIEW_ITEM but no ADD_TO_CART is not abandoned."""
    sessions = sessionize([make_view()])
    assert find_abandoned(sessions) == []


def test_low_value_cart_filtered():
    """Cart value below ``min_cart_vnd`` is dropped."""
    events = [make_add(price=10_000)]  # tiny cart
    sessions = sessionize(events)
    assert find_abandoned(sessions, min_cart_vnd=50_000) == []


def test_idle_timeout_classification():
    events = [make_add(price=200_000)]  # add then session times out
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions)
    assert len(abandoned) == 1
    assert abandoned[0].reason is AbandonReason.IDLE_TIMEOUT


def test_checkout_dropoff_classification():
    events = [
        make_add(price=200_000),
        # START_CHECKOUT without COMPLETE_CHECKOUT.
        make_view(t_min=2),  # placeholder for START_CHECKOUT — use real one:
    ]
    from datetime import timedelta

    from cartrec.schema import EventKind

    from ._fixtures import DEFAULT_TS, make_event

    events = [
        make_add(price=200_000),
        make_event(
            event_id="E-SC",
            kind=EventKind.START_CHECKOUT,
            occurred_at=DEFAULT_TS + timedelta(minutes=3),
            item_id=None,
            unit_price_vnd=None,
        ),
    ]
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions)
    assert len(abandoned) == 1
    assert abandoned[0].reason is AbandonReason.CHECKOUT_DROPOFF


def test_explicit_abandon_classification():
    events = [make_add(price=200_000), make_checkout(t_min=5, complete=False)]
    sessions = sessionize(events)
    abandoned = find_abandoned(sessions)
    assert len(abandoned) == 1
    assert abandoned[0].reason is AbandonReason.EXPLICIT


def test_abandon_rate_excludes_browse_only():
    """Browse-only sessions don't count toward the denominator."""
    events = [
        make_view(buyer_id="B-view"),  # browse-only
        make_add(buyer_id="B-buy", price=100_000),
        make_checkout(buyer_id="B-buy", t_min=5),  # completes
        make_add(buyer_id="B-ab", price=100_000),  # abandons
    ]
    sessions = sessionize(events)
    rate = abandon_rate(sessions)
    # 1 abandoned of 2 carting sessions = 0.5; the browse-only session is excluded.
    assert rate == 0.5


def test_abandon_rate_zero_when_no_carting():
    sessions = sessionize([make_view()])
    assert abandon_rate(sessions) == 0.0


def test_validates_min_cart():
    with pytest.raises(ValueError):
        find_abandoned([], min_cart_vnd=-1)


def test_zero_min_cart_includes_all():
    """min_cart_vnd=0 means even tiny carts count as abandoned."""
    events = [make_add(price=1_000)]
    sessions = sessionize(events)
    assert len(find_abandoned(sessions, min_cart_vnd=0)) == 1
