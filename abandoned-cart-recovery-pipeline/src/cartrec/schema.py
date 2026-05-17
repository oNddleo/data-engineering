"""Cart-funnel event schema.

A VN marketplace (Shopee / Lazada / Tiki / TikTok Shop) emits the
canonical six event kinds below for every buyer journey. The
pipeline folds them into sessions and identifies which ones
abandoned a non-empty cart.

| EventKind         | Meaning                                                      |
| ----------------- | ------------------------------------------------------------ |
| ``VIEW_ITEM``     | Buyer landed on a product detail page                        |
| ``ADD_TO_CART``   | Buyer added an item to cart                                  |
| ``REMOVE_FROM_CART`` | Buyer removed an item from cart                           |
| ``START_CHECKOUT``| Buyer clicked "Place order" — checkout flow started          |
| ``COMPLETE_CHECKOUT``| Order placed, payment confirmed                          |
| ``ABANDON_CHECKOUT``| Buyer explicitly exited the checkout (back button, close)  |

A session is **abandoned** when:

1. It contains ≥ 1 ``ADD_TO_CART`` (not fully offset by removes), and
2. It does not contain ``COMPLETE_CHECKOUT``.

Implicit timeouts (no event for > idle-gap minutes) also close
the session. The session is abandoned if the closing event isn't
``COMPLETE_CHECKOUT`` and the cart had value.

All money is integer VND. Timestamps are timezone-aware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class EventKind(str, Enum):
    """The canonical six events in the cart funnel."""

    VIEW_ITEM = "VIEW_ITEM"
    ADD_TO_CART = "ADD_TO_CART"
    REMOVE_FROM_CART = "REMOVE_FROM_CART"
    START_CHECKOUT = "START_CHECKOUT"
    COMPLETE_CHECKOUT = "COMPLETE_CHECKOUT"
    ABANDON_CHECKOUT = "ABANDON_CHECKOUT"


@dataclass(frozen=True, slots=True)
class Event:
    """One funnel event.

    ``item_id`` and ``unit_price_vnd`` are only set for cart events
    (``ADD_TO_CART`` / ``REMOVE_FROM_CART``); ``VIEW_ITEM`` records
    the item with no price; checkout events leave both ``None``.
    """

    event_id: str
    buyer_id: str
    kind: EventKind
    occurred_at: datetime
    item_id: str | None
    unit_price_vnd: int | None  # before any cart-level discount

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.buyer_id:
            raise ValueError("buyer_id must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.unit_price_vnd is not None and self.unit_price_vnd < 0:
            raise ValueError(f"unit_price_vnd must be >= 0 when set, got {self.unit_price_vnd}")
        # Cart-mutating events must reference an item.
        if self.kind in (EventKind.ADD_TO_CART, EventKind.REMOVE_FROM_CART):
            if not self.item_id:
                raise ValueError(f"{self.kind.value} must include item_id")
            if self.unit_price_vnd is None:
                raise ValueError(f"{self.kind.value} must include unit_price_vnd")


@dataclass(frozen=True, slots=True)
class Session:
    """Folded session for one buyer between idle gaps."""

    session_id: str  # "buyer_id|opened_at_iso"
    buyer_id: str
    started_at: datetime
    ended_at: datetime  # last-event time
    n_events: int
    n_views: int
    n_add: int
    n_remove: int
    cart_value_vnd: int  # net (added - removed)
    distinct_items: int
    started_checkout: bool
    completed_checkout: bool
    explicit_abandon: bool  # buyer hit ABANDON_CHECKOUT

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if not self.buyer_id:
            raise ValueError("buyer_id must be non-empty")
        if self.started_at > self.ended_at:
            raise ValueError("started_at must be <= ended_at")
        if self.n_events < 1:
            raise ValueError(f"n_events must be >= 1, got {self.n_events}")
        if self.cart_value_vnd < 0:
            raise ValueError(
                f"cart_value_vnd must be >= 0 (removes capped at adds), got {self.cart_value_vnd}"
            )


class TouchChannel(str, Enum):
    """The three reactivation channels VN-marketplace CRM uses."""

    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


@dataclass(frozen=True, slots=True)
class CampaignTouch:
    """A scheduled recovery touchpoint for one abandoned session."""

    touch_id: str
    session_id: str
    buyer_id: str
    channel: TouchChannel
    scheduled_at: datetime
    delay_minutes: int  # since session ended

    def __post_init__(self) -> None:
        if not self.touch_id:
            raise ValueError("touch_id must be non-empty")
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if self.delay_minutes < 0:
            raise ValueError(f"delay_minutes must be >= 0, got {self.delay_minutes}")
        if self.scheduled_at.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")


__all__ = [
    "VN_TZ",
    "CampaignTouch",
    "Event",
    "EventKind",
    "Session",
    "TouchChannel",
]
