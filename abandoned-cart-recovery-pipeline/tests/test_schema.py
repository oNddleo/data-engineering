"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from cartrec.schema import VN_TZ, EventKind

from ._fixtures import make_add, make_event, make_view


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_event_kind_has_six_values():
    assert {k.value for k in EventKind} == {
        "VIEW_ITEM",
        "ADD_TO_CART",
        "REMOVE_FROM_CART",
        "START_CHECKOUT",
        "COMPLETE_CHECKOUT",
        "ABANDON_CHECKOUT",
    }


def test_event_rejects_empty_ids():
    with pytest.raises(ValueError):
        make_event(event_id="")
    with pytest.raises(ValueError):
        make_event(buyer_id="")


def test_event_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_event(occurred_at=datetime(2026, 5, 1))


def test_event_rejects_negative_price():
    with pytest.raises(ValueError):
        make_event(unit_price_vnd=-1)


def test_add_to_cart_requires_item():
    with pytest.raises(ValueError, match="ADD_TO_CART"):
        make_event(kind=EventKind.ADD_TO_CART, item_id=None, unit_price_vnd=100)


def test_add_to_cart_requires_price():
    with pytest.raises(ValueError, match="ADD_TO_CART"):
        make_event(kind=EventKind.ADD_TO_CART, item_id="I", unit_price_vnd=None)


def test_remove_from_cart_requires_item():
    with pytest.raises(ValueError):
        make_event(kind=EventKind.REMOVE_FROM_CART, item_id=None, unit_price_vnd=100)


def test_view_can_omit_price():
    """VIEW_ITEM records the item but doesn't need a price."""
    v = make_view()
    assert v.kind is EventKind.VIEW_ITEM
    assert v.unit_price_vnd is None


def test_checkout_omits_item_and_price():
    """Checkout events don't carry per-line item info."""
    from ._fixtures import make_checkout

    c = make_checkout()
    assert c.item_id is None
    assert c.unit_price_vnd is None


def test_zero_price_legal():
    """A free / promo item at 0 VND is legal."""
    a = make_add(price=0)
    assert a.unit_price_vnd == 0
