"""Customer + Order + RFM-score schema.

RFM = Recency / Frequency / Monetary — the classic CRM segmentation
framework. Each of the three dimensions is bucketed into a 1-5
quintile score:

* **R (Recency)** — 5 = most recent buyer, 1 = longest dormant.
* **F (Frequency)** — 5 = most orders, 1 = single-order tail.
* **M (Monetary)** — 5 = highest total spend, 1 = lowest.

The composite ``rfm_string`` is the three scores concatenated
(e.g. ``"555"`` = champion, ``"111"`` = lost). Named segments are
derived from the composite via :class:`Segment`.

All money is integer VND — matches the convention from every other
repo in this catalogue (no Decimal, no float drift).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Segment(str, Enum):
    """Named CRM segments derived from the (R, F, M) score triple.

    The mapping below is the industry-standard one used by Shopee /
    Lazada CRM and most VN marketplaces:

    | R   | F   | Segment           |
    | --- | --- | ----------------- |
    | 5   | 5   | CHAMPIONS         |
    | 5   | 3-4 | LOYAL_CUSTOMERS   |
    | 5   | 1-2 | NEW_CUSTOMERS     |
    | 4   | 4-5 | POTENTIAL_LOYALISTS |
    | 3   | 4-5 | NEED_ATTENTION    |
    | 2-3 | 1-3 | ABOUT_TO_SLEEP    |
    | 1-2 | 4-5 | AT_RISK           |
    | 1   | 4-5 | CANT_LOSE_THEM    |
    | 1   | 1-3 | HIBERNATING       |
    | 1   | 1   | LOST              |
    """

    CHAMPIONS = "CHAMPIONS"
    LOYAL_CUSTOMERS = "LOYAL_CUSTOMERS"
    POTENTIAL_LOYALISTS = "POTENTIAL_LOYALISTS"
    NEW_CUSTOMERS = "NEW_CUSTOMERS"
    NEED_ATTENTION = "NEED_ATTENTION"
    ABOUT_TO_SLEEP = "ABOUT_TO_SLEEP"
    AT_RISK = "AT_RISK"
    CANT_LOSE_THEM = "CANT_LOSE_THEM"
    HIBERNATING = "HIBERNATING"
    LOST = "LOST"


@dataclass(frozen=True, slots=True)
class Customer:
    """One buyer on the marketplace."""

    customer_id: str
    registered_at: datetime
    city_key: str  # "HCMC", "HN", "DN", … for cohort joins

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id must be non-empty")
        if self.registered_at.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        if not self.city_key:
            raise ValueError("city_key must be non-empty")


@dataclass(frozen=True, slots=True)
class Order:
    """One completed order. Money in integer VND."""

    order_id: str
    customer_id: str
    gross_vnd: int
    n_items: int
    placed_at: datetime

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if not self.customer_id:
            raise ValueError("customer_id must be non-empty")
        if self.gross_vnd < 0:
            raise ValueError(f"gross_vnd must be >= 0, got {self.gross_vnd}")
        if self.n_items < 1:
            raise ValueError(f"n_items must be >= 1, got {self.n_items}")
        if self.placed_at.tzinfo is None:
            raise ValueError("placed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RFMScore:
    """One customer's RFM score at a specific ``as_of`` point in time."""

    customer_id: str
    as_of: datetime
    recency_days: int
    frequency: int
    monetary_vnd: int
    r_score: int  # 1-5
    f_score: int  # 1-5
    m_score: int  # 1-5

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id must be non-empty")
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if self.recency_days < 0:
            raise ValueError(f"recency_days must be >= 0, got {self.recency_days}")
        if self.frequency < 0:
            raise ValueError(f"frequency must be >= 0, got {self.frequency}")
        if self.monetary_vnd < 0:
            raise ValueError(f"monetary_vnd must be >= 0, got {self.monetary_vnd}")
        for name, value in (
            ("r_score", self.r_score),
            ("f_score", self.f_score),
            ("m_score", self.m_score),
        ):
            if not 1 <= value <= 5:
                raise ValueError(f"{name} must be in [1, 5], got {value}")

    @property
    def rfm_string(self) -> str:
        """``"555"`` for champions, ``"111"`` for lost."""
        return f"{self.r_score}{self.f_score}{self.m_score}"

    @property
    def composite(self) -> int:
        """Numeric composite for ranking (e.g. ``555``)."""
        return self.r_score * 100 + self.f_score * 10 + self.m_score


__all__ = ["VN_TZ", "Customer", "Order", "RFMScore", "Segment"]
