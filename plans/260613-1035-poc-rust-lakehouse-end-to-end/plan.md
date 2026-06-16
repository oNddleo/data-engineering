---
title: 'POC: Rust-Accelerated End-to-End Lakehouse'
description: >-
  Thin vertical slice proving Postgres -> incremental ELT -> MinIO + Apache
  Iceberg -> Polars (Rust) transforms -> Trino -> Superset, all on local Docker
  Compose with synthetic data.
status: completed
priority: P2
branch: main
tags:
  - poc
  - lakehouse
  - iceberg
  - rust
  - polars
  - trino
  - docker
blockedBy: []
blocks: []
created: '2026-06-13T03:43:03.254Z'
createdBy: 'ck:plan'
source: skill
---

# POC: Rust-Accelerated End-to-End Lakehouse

## Overview

Prove the **core data flow** of the 7-layer reference architecture
(`knowledge/architecture-layer-diagram.md`) with the smallest end-to-end vertical
slice. Not the full platform — one trustworthy path from a transactional source to a
BI dashboard, on a laptop.

**Thesis to prove:** raw operational data can land in an open lakehouse (Iceberg on
object storage), be transformed with a Rust-accelerated engine, and be queried +
visualized through a single federated gateway — reproducibly, with `docker compose up`.

**Scope decisions (locked with user):**
- Vertical slice = end-to-end lakehouse (NOT governance / real-time / EDMS theses).
- Processing = **Rust-accelerated**: Polars (Rust engine) for reads/transforms,
  Lakekeeper (Rust) as Iceberg REST catalog. **PyIceberg (Python) handles writes** —
  pure-Rust Iceberg write/upsert does not exist in production as of 2026 (verified by
  research, see reports). This hybrid matches the user's own `knowledge/DE.md`
  conclusion: "Python to orchestrate, Rust to force performance."
- Runtime = local Docker Compose + synthetic Faker data. No cloud.
- **CDC deferred:** Debezium + Kafka dropped from v1 (saves ~2GB RAM + 3 containers).
  v1 uses watermark-based incremental snapshot ELT, which is sufficient to prove the
  lakehouse thesis the user selected. CDC is an explicit stretch goal, not a silent cut.

## Out of Scope (explicit)
Governance stack (OpenMetadata, Great Expectations beyond a smoke check), security
(Keycloak/OPA), EDMS (Mayan/Tika), API Gateway (Kong), real-time streaming
(Kafka/Debezium/Flink), Data Warehouse (ClickHouse — Trino+Iceberg covers POC query
need). These belong to follow-on plans once the core slice is proven.

## Architecture (POC slice)

```
Postgres (synthetic OLTP)
   │  watermark incremental extract (Python + Polars)
   ▼
Iceberg BRONZE  ──┐
   │ Polars (Rust) transforms          MinIO (S3 object store)
   ▼               ├── physical files ─┘
Iceberg SILVER     │   catalog: Lakekeeper (Rust REST catalog)
   │               │   writes:  PyIceberg (Python)
   ▼               │
Iceberg GOLD ──────┘
   │  federated SQL
   ▼
Trino ──► Superset (dashboard)
   ▲
Airflow (orchestrates extract → load → transform on schedule)
```

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Infrastructure Foundation](./phase-01-infrastructure-foundation.md) | Completed |
| 2 | [Source & Synthetic Data](./phase-02-source-synthetic-data.md) | Completed |
| 3 | [Ingestion to Iceberg Bronze](./phase-03-ingestion-to-iceberg-bronze.md) | Completed |
| 4 | [Rust Transform Medallion](./phase-04-rust-transform-medallion.md) | Completed |
| 5 | [Airflow Orchestration](./phase-05-airflow-orchestration.md) | Completed |
| 6 | [Trino Query & Superset BI](./phase-06-trino-query-superset-bi.md) | Completed |
| 7 | [Acceptance Demo & Docs](./phase-07-acceptance-demo-docs.md) | Completed |

## Key Dependencies
- Docker Desktop with **≥14GB RAM** allocated. Honest peak footprint with the FULL stack up
  (Trino + Airflow LocalExecutor + Superset + MinIO + Lakekeeper + Postgres) is ~11–13GB.
  MVP (P1–P4, no Airflow/Superset) fits in ~6–7GB. Publish a real `docker stats` peak in P7.
- **One shared Postgres** hosts all internal metadata DBs (Lakekeeper catalog, Airflow
  metadata, Superset metadata) as separate logical databases — only the synthetic OLTP
  `source-db` is a distinct instance. Do NOT run four Postgres containers.
- Linear phase order: each phase depends on the previous. P3 needs P1+P2; P5 wires
  P3+P4; P6 needs P4 gold tables.

## Success Criteria (whole POC)
- `docker compose up` brings the full stack healthy on a laptop from a clean clone.
- One Airflow DAG run lands new Postgres rows into Iceberg bronze→silver→gold.
- Trino returns correct aggregates from gold tables; Superset renders ≥1 dashboard.
- A second DAG run **extracts only new/changed rows** (watermark incremental proven at the
  extract boundary — verified via row counts + Iceberg snapshot `added-records`). Applying
  changes as a merge/upsert is a stretch goal; bronze is append-only, dedup happens in silver.
- README lets a new engineer reproduce the demo in <30 min.

## MVP vs Full Slice
**MVP (proves the thesis on its own):** Phases 1–4 + a handful of Trino queries — source →
Iceberg bronze/silver/gold → federated SQL. If time/RAM runs short, this is the shippable core.
**Full slice:** add Phase 5 (Airflow orchestration) and Phase 6 (Superset BI) for the
operational + human-facing story. Treat P5/P6 as the trim line, not the foundation.

## Honesty Note on "Rust-Accelerated"
Rust is genuinely load-bearing in the **catalog (Lakekeeper)** and **read/transform (Polars)**
layers. Writes (PyIceberg) and query (Trino/JVM) are not Rust. So the honest claim is "Rust
where it is production-ready in 2026," not "a pure-Rust stack." A lighter alternative —
**DuckDB** for read+transform+local query — would prove the same end-to-end thesis with less
plumbing; it is documented as the fallback if the Polars/PyIceberg split proves fiddly. The
Rust choice is the user's explicit preference and is retained; this note keeps the claim defensible.

## Reference Reports
- `plans/reports/researcher-260613-1035-rust-iceberg-lakehouse-maturity-report.md`
- `plans/reports/researcher-260613-1035-local-lakehouse-docker-reference-report.md`
