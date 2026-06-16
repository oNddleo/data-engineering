"""Unit tests for the pure Polars transforms — no stack/Iceberg needed.

Feeds tiny hand-built frames to silver + gold functions and asserts the maths,
including the reconciliation invariant gold revenue == bronze line revenue.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import polars as pl
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

from transforms import gold, silver  # noqa: E402


def _ts(day: int) -> datetime:
    return datetime(2026, 1, day, 12, 0, tzinfo=timezone.utc)


def test_dedup_latest_keeps_newest_per_pk():
    df = pl.DataFrame(
        {"id": [1, 1, 2], "v": ["old", "new", "x"], "updated_at": [_ts(1), _ts(2), _ts(1)]}
    )
    out = silver.dedup_latest(df, "id").sort("id")
    assert out.height == 2
    assert out.filter(pl.col("id") == 1)["v"].item() == "new"


def test_clean_products_drops_nonpositive_price():
    df = pl.DataFrame(
        {"id": [1, 2], "price": [10.0, 0.0], "updated_at": [_ts(1), _ts(1)]}
    )
    out = silver.clean_products(df)
    assert out["id"].to_list() == [1]


def _orders():
    return pl.DataFrame(
        {
            "id": [1, 2],
            "customer_id": [10, 20],
            "status": ["paid", "shipped"],
            "order_ts": [_ts(1), _ts(1)],
        }
    )


def _items():
    # order 1: 2*5 + 1*20 = 30 ; order 2: 3*10 = 30  → total 60
    return pl.DataFrame(
        {
            "id": [1, 2, 3],
            "order_id": [1, 1, 2],
            "product_id": [100, 200, 100],
            "quantity": [2, 1, 3],
            "unit_price": [5.0, 20.0, 10.0],
        }
    )


def test_daily_revenue_totals_and_aov():
    out = gold.daily_revenue(_orders(), _items())
    assert out.height == 1
    row = out.row(0, named=True)
    assert row["revenue"] == pytest.approx(60.0)
    assert row["orders"] == 2
    assert row["avg_order_value"] == pytest.approx(30.0)


def test_revenue_by_category_sums_per_category():
    products = pl.DataFrame({"id": [100, 200], "category": ["a", "b"]})
    out = gold.revenue_by_category(_items(), products).sort("category")
    # category a: 2*5 + 3*10 = 40 ; b: 1*20 = 20
    assert dict(zip(out["category"], out["revenue"])) == {"a": pytest.approx(40.0), "b": pytest.approx(20.0)}


def test_top_customers_ltv():
    customers = pl.DataFrame({"id": [10, 20], "name": ["A", "B"], "country": ["US", "VN"]})
    out = gold.top_customers(_orders(), _items(), customers, top_n=10)
    # both customers have LTV 30 -> tie order is unspecified; assert on the mapping, not order
    assert dict(zip(out["customer_id"], out["lifetime_value"])) == {
        10: pytest.approx(30.0),
        20: pytest.approx(30.0),
    }


def test_reconciliation_gold_equals_line_revenue():
    """Invariant: daily_revenue total must equal raw line revenue (the canary)."""
    daily = gold.daily_revenue(_orders(), _items())
    raw = (_items()["quantity"] * _items()["unit_price"]).sum()
    assert daily["revenue"].sum() == pytest.approx(raw)


def test_order_status_funnel_counts():
    out = gold.order_status_funnel(_orders())
    assert out["orders"].sum() == 2
