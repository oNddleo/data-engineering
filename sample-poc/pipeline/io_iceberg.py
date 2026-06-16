"""Iceberg <-> Polars I/O helpers for the transform layer.

Read path uses PyIceberg scan -> Arrow -> Polars (robust against catalog wiring).
The heavy compute (joins/aggregations) runs in Polars' Rust engine — that is where
the "Rust-accelerated" thesis lives. Writes go through PyIceberg.
Swapping the reader to `pl.scan_iceberg` later is a one-function change here.
"""
from __future__ import annotations

import polars as pl

from iceberg_catalog import ensure_table, get_catalog


def read_iceberg(identifier: str) -> pl.DataFrame:
    table = get_catalog().load_table(identifier)
    return pl.from_arrow(table.scan().to_arrow())


def write_iceberg(df: pl.DataFrame, identifier: str, mode: str = "overwrite") -> int:
    """Materialize a Polars frame to an Iceberg table. mode: overwrite | append."""
    arrow = df.to_arrow()
    catalog = get_catalog()
    table = ensure_table(catalog, identifier, arrow.schema)
    if mode == "overwrite":
        table.overwrite(arrow)
    else:
        table.append(arrow)
    return df.height
