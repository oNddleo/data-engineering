"""Test fixtures — keep one canonical builder per record type."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sellermart.schema import VN_TZ
from sellermart.sources import Order, Return, Review

DEFAULT_TS = datetime(2026, 5, 10, 9, 0, 0, tzinfo=VN_TZ)


def make_order(**overrides: Any) -> Order:
    defaults = {
        "order_id": "O-0001",
        "seller_id": 100_001,
        "buyer_id": "B-0001",
        "category_key": "electronics",
        "n_units": 2,
        "gross_vnd": 999_000,
        "created_at": DEFAULT_TS,
    }
    defaults.update(overrides)
    return Order(**defaults)  # type: ignore[arg-type]


def make_return(**overrides: Any) -> Return:
    defaults = {
        "return_id": "RT-0001",
        "order_id": "O-0001",
        "seller_id": 100_001,
        "refund_vnd": 499_000,
        "created_at": DEFAULT_TS,
    }
    defaults.update(overrides)
    return Return(**defaults)  # type: ignore[arg-type]


def make_review(**overrides: Any) -> Review:
    defaults = {
        "review_id": "RV-0001",
        "order_id": "O-0001",
        "seller_id": 100_001,
        "rating_x100": 450,
        "created_at": DEFAULT_TS,
    }
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_order", "make_return", "make_review"]
