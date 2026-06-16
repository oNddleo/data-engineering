# Demo Runbook

A ~10-minute live walkthrough of the lakehouse slice. Assumes Docker has ≥14 GB.

## 0. Clean slate
```bash
make reset            # wipe volumes (safe to skip on first run)
```

## 1. Boot + the cheapest acceptance (MVP)
```bash
make up               # Postgres, MinIO, Lakekeeper, Trino
make ps               # wait until all healthy
make smoke            # creates iceberg.demo.smoke, shows a parquet under s3://warehouse
```
**Show:** MinIO console (http://localhost:9001) → `warehouse` bucket now has objects.
This proves the lakehouse substrate works end to end before any real data.

## 2. Seed synthetic source
```bash
make seed-deps seed-full
```
**Show:** printed counts (customers / products / orders / order_items). Deterministic —
the same after every `make reset`.

## 3. First ELT run (full)
```bash
make pipe-deps
make ingest-bronze-full      # Polars read -> PyIceberg bronze (all rows)
make transform-silver        # dedup latest-per-PK
make transform-gold          # build marts
```
**Show in Trino** (`make trino-cli`, paste from `bi/trino_validation_queries.sql`):
- `SHOW SCHEMAS FROM iceberg` → bronze / silver / gold
- the reconciliation query → `gold_total == silver_line_total` (the canary)

## 4. Prove incremental
```bash
make seed-append             # +500 new orders, ~200 updated rows
make ingest-bronze           # appends ONLY the delta
```
**Show:** the ingest log prints `appended N rows` where N ≈ the delta, NOT the full table.
Then in Trino, inspect snapshots:
```sql
SELECT committed_at, summary['added-records']
FROM iceberg.bronze."orders$snapshots" ORDER BY committed_at;
```
The newest snapshot's `added-records` ≈ the appended delta — incremental proven.
```bash
make transform-silver transform-gold   # silver dedups, gold refreshes
```

## 5. Dashboard (full slice)
```bash
make up-full          # adds Airflow + Superset (first run builds images)
make superset-ui      # http://localhost:8088  (admin/admin)
```
**Show:** in Superset, add datasets on `iceberg.gold.*`, build charts:
- line: `daily_revenue` (order_date × revenue)
- bar: `revenue_by_category`
- table: `top_customers`
- bar: `order_status_funnel`

## 6. Orchestration
```bash
make airflow-ui       # http://localhost:8082  (admin/admin)
make dag-trigger      # runs lakehouse_elt: bronze -> silver -> gold
```
**Show:** the DAG graph + a green run. It reuses the same pipeline code and watermark
store as the manual `make` runs.

## 7. One-command reproduction
```bash
make reset && make demo
```
Boots everything, seeds, runs full + incremental ELT unattended. Capture `make stats`
for the real RAM peak to publish in the README.

## Teardown
```bash
make down-full        # stop (keep volumes)   |   make reset = stop + wipe
```
