---
phase: 2
title: Source & Synthetic Data
status: completed
priority: P1
effort: 0.5d
dependencies:
  - 1
---

# Phase 2: Source & Synthetic Data

## Overview
Create a realistic transactional source: an e-commerce OLTP schema in Postgres seeded with
synthetic data via Faker. Data must support incremental ingestion (timestamps) and
meaningful aggregates (so the dashboard isn't trivial).

## Requirements
- Functional: `customers`, `products`, `orders`, `order_items` tables seeded; every row
  has `created_at` and `updated_at` for watermark-based incremental extract.
- Non-functional: seed completes in < ~90s; volume large enough to show partitioning
  (~100K customers, ~50K products, ~500K orders, ~1.5M order_items) but laptop-friendly.

## Architecture
Domain = e-commerce (well understood, demos joins + time-series + aggregates).
A re-runnable `generate-and-append` mode lets Phase 3/5 prove incremental ingestion by
inserting/updating a fresh batch on demand.

```
seed_source_data.py
  ├── create schema (idempotent, DDL)
  ├── --mode full     → bulk seed baseline
  └── --mode append   → insert N new orders + update M existing (bumps updated_at)
```

## Related Code Files
- Create: `source/schema.sql` (DDL: 4 tables, PKs/FKs, indexes on `updated_at`)
- Create: `source/seed_source_data.py` (Faker generator, `full` + `append` modes)
- Create: `source/pyproject.toml` or `requirements.txt` (faker, psycopg2-binary)
- Modify: `docker-compose.yml` (mount `schema.sql` into source-db init, or run via make)
- Create: `Makefile` targets `seed-full`, `seed-append`

## Implementation Steps
1. Write `schema.sql`: `customers(id, name, email, country, created_at, updated_at)`,
   `products(id, name, category, price, ...)`, `orders(id, customer_id, status,
   order_ts, created_at, updated_at)`, `order_items(id, order_id, product_id, qty,
   unit_price)`. Index `updated_at` on incrementally-extracted tables.
2. `seed_source_data.py` using Faker: deterministic seed (`Faker.seed(42)`) for
   reproducible demos. Batch inserts (`execute_values`) for speed.
3. `--mode full`: seed baseline volumes (configurable via env/CLI).
4. `--mode append`: insert a small batch of new orders + update a few existing rows,
   setting `updated_at = now()`. This is the engine that proves incremental ELT later.
5. Use bulk COPY/`execute_values`; target < 90s on a laptop. Print row counts at end.
6. Add `make seed-full` / `make seed-append`.

## Success Criteria
- [ ] `make seed-full` populates all 4 tables with expected counts (printed summary).
- [ ] `SELECT count(*)` matches targets; FKs valid (no orphan order_items).
- [ ] `make seed-append` adds new orders + bumps `updated_at` on some existing rows.
- [ ] Re-running `seed-full` after `make reset` is reproducible (same seed → same shape).

## Risk Assessment
- **Seed too slow** → use `execute_values`/COPY, not row-by-row inserts.
- **No `updated_at` discipline** → incremental extract in Phase 3 silently misses changes;
  enforce trigger or explicit set in append mode.
- **Volume too high for laptop** → make counts env-configurable; default conservative.
