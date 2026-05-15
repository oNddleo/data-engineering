"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from flashpipe.events import VN_TZ, Event, EventKind


def make_event(
    *,
    event_id: str = "E-1",
    kind: EventKind = EventKind.VIEW,
    user_id: str = "U-1",
    item_id: int = 100_001,
    shop_id: int = 1_000,
    quantity: int = 0,
    amount_vnd: int = 0,
    created_at: datetime | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        kind=kind,
        user_id=user_id,
        item_id=item_id,
        shop_id=shop_id,
        quantity=quantity,
        amount_vnd=amount_vnd,
        created_at=created_at or datetime(2026, 11, 11, 9, 0, 0, tzinfo=VN_TZ),
    )


def t_at(seconds: float) -> datetime:
    return datetime(2026, 11, 11, 9, 0, 0, tzinfo=VN_TZ) + timedelta(seconds=seconds)


__all__ = ["make_event", "t_at"]
