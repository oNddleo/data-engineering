"""Schema for VN review sentiment.

Two data shapes:

* :class:`Review` — what we receive from upstream (Shopee / Lazada /
  Tiki scrapers, or a CRM data warehouse).
* :class:`SentimentResult` — the classifier's output: a 3-way label,
  a normalised confidence in `[0, 1]`, and the raw integer score so
  callers can re-bucket if they want a different threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class SentimentLabel(str, Enum):
    """The three buckets a review can fall into."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class Review:
    """One customer review."""

    review_id: str
    text: str
    seller_id: int
    product_id: int
    category_key: str
    rating_x100: int  # 4.5 stars → 450 (matches shopee-product-scraper-warehouse)
    posted_at: datetime

    def __post_init__(self) -> None:
        if not self.review_id:
            raise ValueError("review_id must be non-empty")
        if self.seller_id <= 0:
            raise ValueError(f"seller_id must be > 0, got {self.seller_id}")
        if self.product_id <= 0:
            raise ValueError(f"product_id must be > 0, got {self.product_id}")
        if not self.category_key:
            raise ValueError("category_key must be non-empty")
        if not 0 <= self.rating_x100 <= 500:
            raise ValueError(f"rating_x100 must be in [0, 500], got {self.rating_x100}")
        if self.posted_at.tzinfo is None:
            raise ValueError("posted_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """One classifier's verdict on one review."""

    review_id: str
    label: SentimentLabel
    score: int
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


__all__ = ["VN_TZ", "Review", "SentimentLabel", "SentimentResult"]
