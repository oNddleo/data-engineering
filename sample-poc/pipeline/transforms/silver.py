"""Bronze -> silver: collapse the append-only log to latest-per-PK + basic cleaning.

Pure functions over Polars frames. This is where append-only bronze becomes a
clean, deduped current-state view — the reason bronze never needs upsert.
"""
from __future__ import annotations

import polars as pl


def dedup_latest(df: pl.DataFrame, pk: str, updated_col: str = "updated_at") -> pl.DataFrame:
    """Keep the newest row per primary key (latest updated_at wins)."""
    if df.is_empty():
        return df
    return df.sort(updated_col).unique(subset=[pk], keep="last", maintain_order=True)


def clean_customers(df: pl.DataFrame) -> pl.DataFrame:
    df = dedup_latest(df, "id")
    return df.drop_nulls(subset=["id", "email"])


def clean_products(df: pl.DataFrame) -> pl.DataFrame:
    df = dedup_latest(df, "id")
    # drop non-positive prices (garbage rows)
    return df.filter(pl.col("price") > 0)


def clean_orders(df: pl.DataFrame) -> pl.DataFrame:
    df = dedup_latest(df, "id")
    return df.drop_nulls(subset=["id", "customer_id"])


def clean_order_items(df: pl.DataFrame) -> pl.DataFrame:
    df = dedup_latest(df, "id")
    return df.filter((pl.col("quantity") > 0) & (pl.col("unit_price") >= 0))
