---
phase: 4
title: Rust Transform Medallion
status: completed
priority: P1
effort: 1.5d
dependencies:
  - 3
---

# Phase 4: Rust Transform Medallion

## Overview
Transform bronze → silver → gold using **Polars (Rust engine)** as the compute layer —
the core of the "Rust-accelerated" thesis. Silver cleans/conforms; gold is
business-ready aggregates the dashboard consumes. Reads from Iceberg via Polars scan;
writes via PyIceberg.

## Requirements
- Functional: `iceberg.silver.*` (cleaned, deduped, typed) and `iceberg.gold.*`
  (aggregated marts) produced deterministically from bronze.
- Non-functional: transforms run lazily (Polars `LazyFrame`); gold refresh on baseline
  data completes in seconds-to-low-minutes on a laptop.

## Architecture
```
iceberg.bronze.*  ──(Polars scan_iceberg, lazy, Rust)──► LazyFrame
   │  silver: dedup on PK (max updated_at), null/type fixes, enrich
   ▼
iceberg.silver.*  ──(Polars joins/aggregations, Rust)──► gold marts
   ▼
iceberg.gold.*    ←─ PyIceberg overwrite/append per mart
```
Medallion layers as Iceberg namespaces. Gold marts (examples):
- `gold.daily_revenue` (date × revenue, orders, AOV)
- `gold.revenue_by_category`
- `gold.top_customers` (LTV)
- `gold.order_status_funnel`

## Related Code Files
- Create: `pipeline/transform_silver.py` (bronze→silver, Polars)
- Create: `pipeline/transform_gold.py` (silver→gold marts, Polars)
- Create: `pipeline/transforms/` (pure functions: `clean_orders`, `build_daily_revenue`, …)
- Create: `pipeline/io_iceberg.py` (shared scan_iceberg read + PyIceberg write helpers)
- Create: `tests/test_transforms.py` (unit tests on transform functions, small frames)
- Create: `Makefile` targets `transform-silver`, `transform-gold`

## Implementation Steps
1. `io_iceberg.py`: `read_iceberg(table) -> pl.LazyFrame` via `pl.scan_iceberg(metadata,
   ...)` against Lakekeeper; `write_iceberg(df, table, mode)` via PyIceberg from Arrow.
2. Silver: dedup bronze on PK keeping latest `updated_at` (Polars `.sort().unique()` or
   window), enforce types (decimal price, non-null keys), drop test/garbage rows.
3. Gold: build each mart as a pure function taking silver LazyFrames → DataFrame; keep
   transforms in `transforms/` so they're unit-testable without the stack.
4. Materialize: collect LazyFrame → Arrow → PyIceberg write. Gold marts use
   `overwrite` (small, fully recomputed) for POC simplicity; document the choice.
5. Partition gold time-series marts by date where it helps Trino pruning.
6. Unit tests: feed tiny synthetic frames to transform functions, assert aggregates.
7. Validate in Trino: gold counts/sums reconcile against a direct bronze aggregate
   (a basic data-quality smoke check — the only governance touch in this POC).

## Success Criteria
- [ ] `iceberg.silver.*` deduped + typed; row counts ≤ bronze (dedup proven).
- [ ] `iceberg.gold.*` marts populated; `daily_revenue` sum reconciles with bronze total
      (±0 — exact match) via a Trino cross-check query.
- [ ] Transforms run through Polars LazyFrame (Rust engine), not pandas.
- [ ] `pytest tests/test_transforms.py` passes (transform logic covered independent of stack).
- [ ] Re-running transforms is deterministic (same inputs → identical gold).

## Risk Assessment
- **`scan_iceberg` read compatibility with Lakekeeper REST** → if Polars iceberg scan
  struggles, read via PyIceberg `scan().to_arrow()` then `pl.from_arrow()`. Keep read
  behind `io_iceberg.read_iceberg` so the swap is one place. (Verified: Polars iceberg
  read is mature; this is a low-prob fallback.)
- **Gold overwrite races with concurrent ingest** → POC runs phases sequentially in the
  DAG; note that incremental gold is out of POC scope.
- **Reconciliation mismatch** → usually a dedup/type bug; the Trino cross-check in success
  criteria is the canary.
