"""Silver -> gold: business-ready marts the dashboard consumes.

Pure functions over Polars frames. Revenue is computed as a Float64 for BI
friendliness (line_revenue = quantity * unit_price).
"""
from __future__ import annotations

import polars as pl

_LINE_REVENUE = (pl.col("quantity").cast(pl.Float64) * pl.col("unit_price").cast(pl.Float64)).alias(
    "line_revenue"
)


def _items_with_revenue(order_items: pl.DataFrame) -> pl.DataFrame:
    return order_items.with_columns(_LINE_REVENUE)


def daily_revenue(orders: pl.DataFrame, order_items: pl.DataFrame) -> pl.DataFrame:
    items = _items_with_revenue(order_items)
    joined = items.join(orders.select(["id", "order_ts"]), left_on="order_id", right_on="id")
    return (
        joined.with_columns(pl.col("order_ts").dt.date().alias("order_date"))
        .group_by("order_date")
        .agg(
            pl.col("line_revenue").sum().round(2).alias("revenue"),
            pl.col("order_id").n_unique().alias("orders"),
        )
        .with_columns((pl.col("revenue") / pl.col("orders")).round(2).alias("avg_order_value"))
        .sort("order_date")
    )


def revenue_by_category(order_items: pl.DataFrame, products: pl.DataFrame) -> pl.DataFrame:
    items = _items_with_revenue(order_items)
    joined = items.join(products.select(["id", "category"]), left_on="product_id", right_on="id")
    return (
        joined.group_by("category")
        .agg(pl.col("line_revenue").sum().round(2).alias("revenue"))
        .sort("revenue", descending=True)
    )


def top_customers(
    orders: pl.DataFrame, order_items: pl.DataFrame, customers: pl.DataFrame, top_n: int = 20
) -> pl.DataFrame:
    items = _items_with_revenue(order_items)
    by_customer = (
        items.join(orders.select(["id", "customer_id"]), left_on="order_id", right_on="id")
        .group_by("customer_id")
        .agg(pl.col("line_revenue").sum().round(2).alias("lifetime_value"))
    )
    return (
        by_customer.join(
            customers.select(["id", "name", "country"]), left_on="customer_id", right_on="id"
        )
        .sort("lifetime_value", descending=True)
        .head(top_n)
    )


def order_status_funnel(orders: pl.DataFrame) -> pl.DataFrame:
    return (
        orders.group_by("status")
        .agg(pl.len().alias("orders"))
        .sort("orders", descending=True)
    )
