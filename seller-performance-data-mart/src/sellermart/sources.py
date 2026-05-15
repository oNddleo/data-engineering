"""Source-system records that flow into the fact table.

These are the upstream shapes the ETL consumes:

* :class:`Order`  — one order line (transactional).
* :class:`Return` — refunds + RMAs, joined to an order via ``order_id``.
* :class:`Review` — buyer reviews; one per ``(order_id, buyer_id)``.

The ETL collapses these three streams into one
:class:`FactSellerDay` row per ``(seller_id, day_in_VN_TZ)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class Order:
    """One Shopee/Lazada-style order line."""

    order_id: str
    seller_id: int
    buyer_id: str
    category_key: str
    n_units: int
    gross_vnd: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if self.seller_id <= 0:
            raise ValueError(f"seller_id must be > 0, got {self.seller_id}")
        if not self.buyer_id:
            raise ValueError("buyer_id must be non-empty")
        if self.n_units < 1:
            raise ValueError(f"n_units must be >= 1, got {self.n_units}")
        if self.gross_vnd < 0:
            raise ValueError(f"gross_vnd must be >= 0, got {self.gross_vnd}")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Return:
    """One returned order (full or partial refund). One per order_id."""

    return_id: str
    order_id: str
    seller_id: int
    refund_vnd: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.return_id:
            raise ValueError("return_id must be non-empty")
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if self.seller_id <= 0:
            raise ValueError(f"seller_id must be > 0, got {self.seller_id}")
        if self.refund_vnd < 0:
            raise ValueError(f"refund_vnd must be >= 0, got {self.refund_vnd}")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Review:
    """One review left for an order."""

    review_id: str
    order_id: str
    seller_id: int
    rating_x100: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.review_id:
            raise ValueError("review_id must be non-empty")
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if self.seller_id <= 0:
            raise ValueError(f"seller_id must be > 0, got {self.seller_id}")
        if not 0 <= self.rating_x100 <= 500:
            raise ValueError(f"rating_x100 must be in [0, 500], got {self.rating_x100}")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


__all__ = ["Order", "Return", "Review"]
