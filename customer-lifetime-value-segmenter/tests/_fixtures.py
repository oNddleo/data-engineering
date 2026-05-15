"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from clvseg.schema import VN_TZ, Customer, Order, RFMScore

DEFAULT_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


def make_customer(**overrides: Any) -> Customer:
    defaults = {
        "customer_id": "C-0001",
        "registered_at": DEFAULT_TS - timedelta(days=365),
        "city_key": "HCMC",
    }
    defaults.update(overrides)
    return Customer(**defaults)  # type: ignore[arg-type]


def make_order(**overrides: Any) -> Order:
    defaults = {
        "order_id": "O-0001",
        "customer_id": "C-0001",
        "gross_vnd": 500_000,
        "n_items": 2,
        "placed_at": DEFAULT_TS - timedelta(days=5),
    }
    defaults.update(overrides)
    return Order(**defaults)  # type: ignore[arg-type]


def make_score(**overrides: Any) -> RFMScore:
    defaults = {
        "customer_id": "C-0001",
        "as_of": DEFAULT_TS,
        "recency_days": 5,
        "frequency": 3,
        "monetary_vnd": 1_500_000,
        "r_score": 5,
        "f_score": 3,
        "m_score": 4,
    }
    defaults.update(overrides)
    return RFMScore(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_customer", "make_order", "make_score"]
