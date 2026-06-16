---
phase: 1
title: Infrastructure Foundation
status: completed
priority: P1
effort: 1d
dependencies: []
---

# Phase 1: Infrastructure Foundation

## Overview
Stand up the local lakehouse substrate with Docker Compose: object store, Iceberg REST
catalog, query engine, source DB, and a shared network. Everything downstream depends on
this booting cleanly and reproducibly.

## Requirements
- Functional: `docker compose up -d` brings MinIO, Lakekeeper, Trino, Postgres healthy.
  Iceberg warehouse bucket exists. Trino can list the Iceberg catalog (empty is fine).
- Non-functional: total idle footprint < ~6GB RAM (Airflow/Superset added later);
  deterministic startup via healthchecks + `depends_on: condition: service_healthy`.

## Architecture
Single Compose project on one explicit bridge network. Service DNS names used everywhere
(NOT `localhost`) — this is the #1 docker lakehouse failure mode.

| Service | Image (pin a tag) | Role | Notes |
|---------|-------------------|------|-------|
| `minio` | `minio/minio` | S3 object store | console 9001, api 9000 |
| `mc` (init) | `minio/mc` | one-shot bucket bootstrap | creates `warehouse` bucket, exits |
| `lakekeeper` | `quay.io/lakekeeper/catalog` | Iceberg REST catalog (Rust) | requires a Postgres metadata DB (it is NOT embedded) |
| `meta-db` | `postgres` | **shared** metadata store | hosts `lakekeeper`, later `airflow`, `superset` DBs as separate logical databases |
| `trino` | `trinodb/trino` | federated query engine | Iceberg connector → Lakekeeper REST |
| `source-db` | `postgres` | synthetic OLTP source (Phase 2) | the ONLY separate Postgres; named `source-db` to avoid clash |

> Lakekeeper 0.12 needs an external Postgres for its metadata (research artifacts disagreed;
> resolved here as: external, on the shared `meta-db`). Phases 5/6 add `airflow`/`superset`
> databases to this same `meta-db` instead of spawning new Postgres containers.

## Related Code Files
- Create: `docker-compose.yml`
- Create: `.env.example` (credentials, ports, `AWS_REGION`, MinIO keys)
- Create: `infra/minio/bootstrap.sh` (mc bucket creation)
- Create: `infra/trino/catalog/iceberg.properties` (Iceberg REST + S3 wiring)
- Create: `infra/trino/config.properties`, `infra/trino/jvm.config` (lean memory)
- Create: `infra/lakekeeper/bootstrap` notes (warehouse registration call)
- Create: `Makefile` (`up`, `down`, `ps`, `logs`, `reset` targets)

## Implementation Steps
1. Write `docker-compose.yml` with the 6 services above on one bridge network; pin image
   tags (avoid `latest`). Add healthchecks: MinIO `/minio/health/live`, Postgres
   `pg_isready`, Trino `/v1/info` returns `starting:false`, Lakekeeper `/health`.
2. `mc` init container: wait for MinIO, `mc alias set`, `mc mb --ignore-existing
   minio/warehouse`. Iceberg REST will NOT auto-create the bucket.
3. Configure Trino Iceberg connector (`iceberg.properties`). **Pin ONE Trino version first**
   (e.g. a recent `trinodb/trino` release) and use its exact property names — the S3 filesystem
   property generation changed across versions, and mixing them is a top failure mode. For a
   current Trino with the native S3 filesystem:
   - `connector.name=iceberg`
   - `iceberg.catalog.type=rest`
   - `iceberg.rest-catalog.uri=http://lakekeeper:8181/catalog`
   - `iceberg.rest-catalog.warehouse=<warehouse-id registered in Lakekeeper>` (the catalog
     warehouse identifier from step 5 — NOT the literal string `s3://warehouse`)
   - `fs.native-s3.enabled=true`
   - `s3.endpoint=http://minio:9000`, `s3.path-style-access=true` (mandatory for MinIO),
     `s3.region=us-east-1`, `s3.aws-access-key=…`, `s3.aws-secret-key=…`
   - If the pinned Trino predates native-s3, swap to the legacy `hive.s3.*` / `fs.s3.*`
     equivalents — do not mix generations. Verify against THAT version's docs, not memory.
4. Trim Trino memory in `jvm.config` (`-Xmx2G`) and `config.properties`
   (`query.max-memory-per-node`) so it fits a laptop.
5. Register the Lakekeeper warehouse (one-time REST call / init step) pointing at
   `s3://warehouse` with the MinIO endpoint + path-style.
6. Add `Makefile` convenience targets + a `make reset` that wipes volumes for clean reruns.
7. Smoke test: `trino> SHOW CATALOGS;` shows `iceberg`; `CREATE SCHEMA iceberg.demo;`
   succeeds and writes metadata to MinIO.

## Success Criteria
- [ ] `docker compose up -d` → all services report healthy within ~90s.
- [ ] MinIO console shows `warehouse` bucket.
- [ ] Trino `SHOW CATALOGS` lists `iceberg`; `CREATE SCHEMA iceberg.demo` succeeds.
- [ ] Creating a throwaway Iceberg table writes Parquet + metadata under `s3://warehouse`.
- [ ] `make reset` returns to a clean slate.

## Risk Assessment
- **MinIO virtual-host addressing fails in Docker** → always set `s3.path-style-access=true`.
- **`localhost` vs service DNS** → use `minio:9000`, `lakekeeper:8181` everywhere.
- **Lakekeeper warehouse not registered** → Trino errors on first table; add explicit
  registration step + verify in logs.
- **Image tag drift** → pin tags; record exact versions in README.
