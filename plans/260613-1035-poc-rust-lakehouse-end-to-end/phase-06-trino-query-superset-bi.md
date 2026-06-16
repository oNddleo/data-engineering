---
phase: 6
title: Trino Query & Superset BI
status: completed
priority: P2
effort: 1d
dependencies:
  - 4
---

# Phase 6: Trino Query & Superset BI

## Overview
Close the loop: serve gold marts through Trino (federated query gateway, architecture L7)
and visualize them in a Superset dashboard. This is the human-facing proof that the
lakehouse delivers business value, not just plumbing.

## Requirements
- Functional: Superset connects to Trino, queries `iceberg.gold.*`, renders ≥1 dashboard
  with ≥3 charts driven by gold marts.
- Non-functional: Superset added only if RAM allows (~1.5GB). If the laptop is tight,
  Trino SQL + saved query screenshots are an acceptable v1 fallback (documented).

## Architecture
```
iceberg.gold.* ──► Trino (SQLAlchemy: trino://) ──► Superset datasets ──► charts ──► dashboard
```
- Connection: `trino://user@trino:8080/iceberg` via `sqlalchemy-trino`/`trino` driver.
- Superset metadata = a `superset` database on the shared `meta-db` Postgres (Phase 1) — do
  NOT add a new Postgres container. SQLite is an even-lighter fallback for an absolute-minimal POC.
- Dashboard: "E-commerce Lakehouse Overview" — revenue trend, revenue by category,
  top customers, order-status funnel.

## Related Code Files
- Modify: `docker-compose.yml` (superset, superset-init; metadata = `superset` DB on shared `meta-db`)
- Create: `bi/superset/bootstrap.sh` (db upgrade, admin, init; register Trino DB)
- Create: `bi/superset/datasources.yaml` or import bundle (Trino connection + datasets)
- Create: `bi/trino_validation_queries.sql` (reconciliation + demo queries, reusable)
- Create: `Makefile` targets `bi-up`, `bi-import`

## Implementation Steps
1. Author `bi/trino_validation_queries.sql`: the demo aggregates + a reconciliation query
   (gold vs bronze totals) reused from Phase 4's success check.
2. Add Superset services to Compose (webserver port 8088, init container for
   `superset db upgrade`, `fab create-admin`, `superset init`).
3. Register Trino as a Superset database: `trino://admin@trino:8080/iceberg`. Verify the
   connection test passes (catalog `iceberg` reachable).
4. Create datasets on `iceberg.gold.*` marts; build 3–4 charts (time-series line, bar,
   table) and assemble one dashboard.
5. Export the dashboard/datasets as an importable bundle so the demo is reproducible from
   a clean stack (`make bi-import`), not click-built each time.
6. RAM check: if over budget, drop Superset metadata Postgres → SQLite, or document the
   Trino-only fallback and ship screenshots.

## Success Criteria
- [ ] Superset connects to Trino; `iceberg.gold.*` datasets load.
- [ ] One dashboard with ≥3 charts renders correct numbers (match Trino SQL).
- [ ] Dashboard is reproducible from clean stack via import bundle (not manual rebuild).
- [ ] `bi/trino_validation_queries.sql` runs in Trino and reconciles gold vs bronze.
- [ ] Full stack (incl. Superset) still fits the laptop RAM budget, or fallback documented.

## Risk Assessment
- **Superset↔Trino driver/auth fiddliness** → use the documented `trino://` SQLAlchemy URI;
  Trino dev auth (no password) for POC; pin Superset + trino driver versions.
- **RAM pressure with full stack up** → Superset is the trim candidate; keep the Trino-only
  fallback as a real, documented option, not an afterthought.
- **Hand-built dashboard not reproducible** → export/import bundle is a hard requirement,
  not optional polish.
