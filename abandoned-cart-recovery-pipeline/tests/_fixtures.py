"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from cartrec.schema import VN_TZ, Event, EventKind

DEFAULT_TS = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)


def make_event(**overrides: Any) -> Event:
    defaults: dict[str, Any] = {
        "event_id": "E-0001",
        "buyer_id": "B-0001",
        "kind": EventKind.VIEW_ITEM,
        "occurred_at": DEFAULT_TS,
        "item_id": "ITEM-1",
        "unit_price_vnd": 99_000,
    }
    defaults.update(overrides)
    return Event(**defaults)


def make_view(buyer_id: str = "B-0001", t_min: int = 0, item: str | None = "ITEM-1") -> Event:
    return make_event(
        event_id=f"E-V-{buyer_id}-{t_min}",
        buyer_id=buyer_id,
        kind=EventKind.VIEW_ITEM,
        occurred_at=DEFAULT_TS + timedelta(minutes=t_min),
        item_id=item,
        unit_price_vnd=None,
    )


def make_add(
    buyer_id: str = "B-0001", t_min: int = 1, item: str = "ITEM-1", price: int = 99_000
) -> Event:
    return make_event(
        event_id=f"E-A-{buyer_id}-{t_min}",
        buyer_id=buyer_id,
        kind=EventKind.ADD_TO_CART,
        occurred_at=DEFAULT_TS + timedelta(minutes=t_min),
        item_id=item,
        unit_price_vnd=price,
    )


def make_remove(
    buyer_id: str = "B-0001", t_min: int = 2, item: str = "ITEM-1", price: int = 99_000
) -> Event:
    return make_event(
        event_id=f"E-R-{buyer_id}-{t_min}",
        buyer_id=buyer_id,
        kind=EventKind.REMOVE_FROM_CART,
        occurred_at=DEFAULT_TS + timedelta(minutes=t_min),
        item_id=item,
        unit_price_vnd=price,
    )


def make_checkout(buyer_id: str = "B-0001", t_min: int = 5, complete: bool = True) -> Event:
    kind = EventKind.COMPLETE_CHECKOUT if complete else EventKind.ABANDON_CHECKOUT
    return make_event(
        event_id=f"E-C-{buyer_id}-{t_min}",
        buyer_id=buyer_id,
        kind=kind,
        occurred_at=DEFAULT_TS + timedelta(minutes=t_min),
        item_id=None,
        unit_price_vnd=None,
    )


__all__ = [
    "DEFAULT_TS",
    "make_add",
    "make_checkout",
    "make_event",
    "make_remove",
    "make_view",
]
