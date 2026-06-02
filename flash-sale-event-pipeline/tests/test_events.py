"""Event invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from flashpipe.events import VN_TZ, EventKind

from ._fixtures import make_event


def test_event_kind_enum():
    assert {k.value for k in EventKind} == {
        "VIEW",
        "ADD_TO_CART",
        "CHECKOUT",
        "ORDER",
        "INVENTORY_UPDATE",
    }


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_event_happy_path():
    e = make_event(kind=EventKind.ORDER, quantity=2, amount_vnd=200_000)
    assert e.kind is EventKind.ORDER
    assert e.quantity == 2


def test_event_rejects_empty_id():
    with pytest.raises(ValueError):
        make_event(event_id="")


def test_event_rejects_empty_user_id_for_view():
    with pytest.raises(ValueError):
        make_event(user_id="")


def test_event_allows_empty_user_for_inventory_update():
    e = make_event(kind=EventKind.INVENTORY_UPDATE, user_id="")
    assert e.user_id == ""


def test_event_rejects_non_positive_item_id():
    with pytest.raises(ValueError):
        make_event(item_id=0)


def test_event_rejects_negative_amount():
    with pytest.raises(ValueError):
        make_event(amount_vnd=-1)


def test_event_rejects_negative_quantity():
    with pytest.raises(ValueError):
        make_event(quantity=-1)


def test_event_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_event(created_at=datetime(2026, 11, 11, 9, 0))
