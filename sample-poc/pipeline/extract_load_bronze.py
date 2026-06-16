"""Extract from source Postgres (Polars/Rust) → load into Iceberg bronze (PyIceberg).

Bronze is an APPEND-ONLY raw log. Incremental at the EXTRACT boundary:
each run reads only rows where updated_at > last watermark, appends them, then
advances the watermark. Dedup/latest-wins happens later in silver (Phase 4).

  python extract_load_bronze.py            # incremental (default)
  python extract_load_bronze.py --full     # reset bronze + reload everything
"""
from __future__ import annotations

import argparse
from datetime import datetime

import polars as pl

import settings
import watermark
from config import TABLES, TableSpec
from iceberg_catalog import ensure_namespace, ensure_table, get_catalog


def _read_delta(spec: TableSpec, since: str, full: bool) -> pl.DataFrame:
    if not full:
        # `since` comes from our own control file; validate it parses as a timestamp
        # before interpolating — closes the SQL trust boundary on the WHERE clause.
        datetime.fromisoformat(since)
    where = "" if full else f"WHERE {spec.watermark_col} > '{since}'::timestamptz"
    query = f"SELECT * FROM {spec.name} {where}"
    return pl.read_database_uri(query, settings.SOURCE_DB_URI, engine="connectorx")


def _max_watermark(df: pl.DataFrame, col: str) -> str | None:
    value = df.select(pl.col(col).max()).item()
    return None if value is None else value.isoformat()


def ingest_table(catalog, spec: TableSpec, full: bool) -> dict[str, str]:
    identifier = f"{settings.NS_BRONZE}.{spec.name}"
    since = watermark.get(spec.name)

    if full and catalog.table_exists(identifier):
        catalog.drop_table(identifier)

    df = _read_delta(spec, since, full)
    if df.is_empty():
        print(f"  {spec.name:12s} no new rows (watermark {since})")
        return {}

    arrow = df.to_arrow()
    table = ensure_table(catalog, identifier, arrow.schema)
    # Conform each delta to the table's established schema so incremental appends
    # don't fail on null-width / decimal-precision drift across runs ("dies on run 2").
    arrow = arrow.cast(table.schema().as_arrow())
    table.append(arrow)

    new_wm = _max_watermark(df, spec.watermark_col)
    print(f"  {spec.name:12s} appended {df.height:>8,} rows  -> watermark {new_wm}")
    return {spec.name: new_wm} if new_wm else {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="reset bronze and reload all rows")
    args = ap.parse_args()

    catalog = get_catalog()
    ensure_namespace(catalog, settings.NS_BRONZE)

    print(f"ingest bronze ({'full' if args.full else 'incremental'}):")
    advanced: dict[str, str] = {}
    failures: list[str] = []
    for spec in TABLES:
        # Per-table isolation: one table failing must not abort the others, and a
        # failed table must not advance its watermark (it retries next run).
        try:
            advanced.update(ingest_table(catalog, spec, args.full))
        except Exception as exc:  # noqa: BLE001 — POC: report + continue, fail at end
            print(f"  {spec.name:12s} FAILED: {exc}")
            failures.append(spec.name)

    if advanced:
        watermark.set_many(advanced)
    print(f"done. advanced {len(advanced)} table(s); {len(failures)} failed.")
    if failures:
        raise SystemExit(f"ingest failed for: {', '.join(failures)}")


if __name__ == "__main__":
    main()
