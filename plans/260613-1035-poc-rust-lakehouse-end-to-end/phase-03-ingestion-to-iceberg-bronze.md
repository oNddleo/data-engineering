---
phase: 3
title: Ingestion to Iceberg Bronze
status: completed
priority: P1
effort: 1.5d
dependencies:
  - 1
  - 2
---

# Phase 3: Ingestion to Iceberg Bronze

## Overview
Move data from Postgres into the lakehouse bronze layer (raw, append/merge as-is) as
Iceberg tables registered in Lakekeeper, stored on MinIO. This is where the
**Rust/Python division of labor** becomes concrete: Polars (Rust) reads, PyIceberg
(Python) writes — because no production pure-Rust Iceberg write path exists in 2026.

## Requirements
- Functional: each source table lands as `iceberg.bronze.<table>`. A watermark column
  (`updated_at`) drives incremental extract: second run ingests only new/changed rows.
- Non-functional: idempotent re-runs (no duplicate explosion); watermark persisted across
  runs; bronze write of baseline volume completes in minutes on a laptop.

## Architecture
```
Postgres ──(Polars read_database / connectorx, Rust engine)──► Polars DataFrame
   │  filter updated_at > last_watermark
   ▼
Arrow table ──(PyIceberg append / upsert)──► iceberg.bronze.<table> on MinIO
   │
   └─ watermark store: small JSON/Iceberg control table updated after each load
```
- **Read:** Polars `read_database`/connectorx — Rust-native, fast Arrow ingestion.
- **Write (PRIMARY): append-only.** Bronze is an immutable raw log — `Table.append()` of the
  watermark delta each run. Dedup/latest-wins is resolved downstream in silver (Phase 4).
  This is the contract the POC commits to, because PyIceberg `upsert` is NOT validated by
  research (only `append` is proven mature in 2026).
- **Write (STRETCH, optional): `upsert()`** keyed on PK — only attempt after the append path
  works end-to-end; if flaky, drop it without affecting any success criterion.
- **Watermark:** persisted per table; default load is incremental at the EXTRACT boundary
  (`WHERE updated_at > last_watermark`), with a `--full` reset.

## Related Code Files
- Create: `pipeline/extract_load_bronze.py` (Polars read → PyIceberg write, per table)
- Create: `pipeline/iceberg_catalog.py` (PyIceberg RestCatalog client → Lakekeeper, shared)
- Create: `pipeline/watermark.py` (read/write last-processed watermark)
- Create: `pipeline/config.py` (table list, PK + watermark column mapping)
- Create: `pipeline/pyproject.toml` (polars, pyiceberg[s3fs,pyarrow], connectorx)
- Create: `Makefile` target `ingest-bronze`

## Implementation Steps
1. `iceberg_catalog.py`: construct PyIceberg `RestCatalog` pointing at Lakekeeper
   (`uri=http://lakekeeper:8181/catalog`, `warehouse`, S3 endpoint=MinIO, path-style).
   Create `bronze` namespace if absent.
2. `config.py`: declare tables with `{name, primary_key, watermark_col}`.
3. `extract_load_bronze.py`:
   - read `last_watermark` (Phase `watermark.py`); build `SELECT ... WHERE updated_at > :wm`.
   - `pl.read_database(...)` into a Polars DataFrame (Rust engine).
   - on first run / `--full`: create table from Arrow schema, `append`.
   - on incremental: **`table.append(delta_arrow)`** — append the watermark delta to the raw
     bronze log (updated rows appear as new versions; silver collapses to latest by PK).
   - advance + persist watermark to `max(updated_at)` of the batch only on success.
   - (Stretch only) optionally try `table.upsert(arrow_table, join_cols=[pk])`; gate behind a
     flag, default off.
4. Schema mapping: ensure Postgres types → Arrow → Iceberg types are stable (timestamps,
   decimals for price). Pin decimal precision to avoid drift.
5. Verify in Trino: `SELECT count(*) FROM iceberg.bronze.orders` matches source.
6. Run `seed-append` (Phase 2) then re-ingest: confirm only the delta was written
   (inspect Iceberg snapshot history / added-records metric).

## Success Criteria
- [ ] All 4 source tables exist as `iceberg.bronze.*`, queryable in Trino. After a `--full`
      load, distinct-PK counts match source.
- [ ] Second run after `seed-append` **appends ONLY the watermark delta** (rows added =
      delta size, verified via Iceberg snapshot `added-records` — not a full rewrite).
- [ ] Re-running with no source changes is a no-op (watermark unchanged, zero new snapshot rows).
- [ ] Polars performs the DB read; PyIceberg performs the write (division of labor honored).
- [ ] Append-only path works WITHOUT relying on `upsert` (upsert is stretch, not required).

## Risk Assessment
- **PyIceberg `upsert` maturity** → already de-risked: append-only bronze + silver dedup
  (Phase 4, Polars window on PK + max(updated_at)) is the PRIMARY contract; upsert is stretch
  only. No success criterion depends on upsert.
- **Watermark gaps from clock skew / equal timestamps** → use `>` with a tie-break on PK,
  or store last `(updated_at, id)` cursor.
- **Type coercion drift** (decimal/timestamp) → pin schema explicitly on table create.
- **connectorx/polars DB driver issues** → fallback to `pyarrow`/`adbc` reader; keep read
  layer swappable behind one function.
