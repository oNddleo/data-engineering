"""Flash-sale event types.

Five event kinds that a typical mobile shopping app emits during a
flash-sale window:

* `VIEW` — user opened a product detail page
* `ADD_TO_CART` — user tapped "Add to cart"
* `CHECKOUT` — user initiated checkout
* `ORDER` — order placed (final conversion)
* `INVENTORY_UPDATE` — backend re-published stock for a product

All carry a ``created_at`` (when the user clicked / when the
backend produced the event) — this is the "event time" we use for
watermarking. Production also has a separate ``ingested_at`` which
we don't bundle because the pipeline measures latency itself in
:mod:`flashpipe.metrics`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class EventKind(str, Enum):
    """The five flash-sale event kinds."""

    VIEW = "VIEW"
    ADD_TO_CART = "ADD_TO_CART"
    CHECKOUT = "CHECKOUT"
    ORDER = "ORDER"
    INVENTORY_UPDATE = "INVENTORY_UPDATE"


@dataclass(frozen=True, slots=True)
class Event:
    """A single flash-sale event in the input stream."""

    event_id: str
    kind: EventKind
    user_id: str
    item_id: int
    shop_id: int
    quantity: int
    amount_vnd: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.user_id and self.kind is not EventKind.INVENTORY_UPDATE:
            raise ValueError(f"user_id must be non-empty for {self.kind.value}")
        if self.item_id <= 0:
            raise ValueError(f"item_id must be > 0, got {self.item_id}")
        if self.shop_id <= 0:
            raise ValueError(f"shop_id must be > 0, got {self.shop_id}")
        if self.quantity < 0:
            raise ValueError(f"quantity must be >= 0, got {self.quantity}")
        if self.amount_vnd < 0:
            raise ValueError(f"amount_vnd must be >= 0, got {self.amount_vnd}")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


__all__ = ["VN_TZ", "Event", "EventKind"]
