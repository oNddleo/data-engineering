"""Silver: cleaned current-state + price history."""

from __future__ import annotations

from typing import Any

import duckdb
from dagster import MaterializeResult, asset

from ..iceberg_utils import overwrite_table, scan, upsert_table


@asset(  # type: ignore[misc]
    group_name="silver",
    compute_kind="duckdb",
    deps=["bronze_listings"],
    description="Deduped current snapshot of each listing (latest scrape per id).",
)
def silver_listings(context: Any) -> MaterializeResult:
    raw = scan("bronze_listings")
    con = duckdb.connect()
    con.register("raw", raw)
    cleaned = con.execute(
        """
        SELECT
          id, title, city, property_type, listing_type,
          rooms, size_m2, price, currency,
          CAST(price AS DOUBLE) / NULLIF(size_m2, 0) AS price_per_m2,
          year_built, lat, lon, seller,
          scraped_at, fingerprint
        FROM (
          SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY scraped_at DESC) rn
          FROM raw
          WHERE price > 0 AND size_m2 > 0
        )
        WHERE rn = 1
        """
    ).arrow()
    full = overwrite_table("silver_listings", cleaned)
    return MaterializeResult(metadata={"rows": cleaned.num_rows, "iceberg_table": full})


@asset(  # type: ignore[misc]
    group_name="silver",
    compute_kind="duckdb",
    deps=["bronze_listings"],
    description="Append-only price history: every observed (id, fingerprint) "
    "becomes a row. Enables time-travel analytics without Delta/SCD2.",
)
def silver_price_history(context: Any) -> MaterializeResult:
    raw = scan("bronze_listings")
    con = duckdb.connect()
    con.register("raw", raw)
    hist = con.execute(
        """
        SELECT DISTINCT id, fingerprint, price, scraped_at
        FROM raw
        """
    ).arrow()
    full = upsert_table("silver_price_history", hist)
    return MaterializeResult(metadata={"rows": hist.num_rows, "iceberg_table": full})
