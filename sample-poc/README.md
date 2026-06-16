# sample-poc — Rust-Accelerated End-to-End Lakehouse

A thin **vertical slice** of an enterprise 7-layer data architecture
([../knowledge/architecture-layer-diagram.md](../knowledge/architecture-layer-diagram.md)):
prove that operational data can land in an open lakehouse (Apache Iceberg on object
storage), be transformed by a Rust-accelerated engine (Polars), and be queried +
visualized through a single federated gateway (Trino + Superset) — reproducibly on a
laptop with `docker compose`.

> A POC, not the full platform. Governance, security, EDMS, API gateway, real-time CDC
> and the warehouse layer are intentionally out of scope. See
> [docs/poc-architecture.md](docs/poc-architecture.md).

## Pipeline

```
Postgres (synthetic OLTP, Faker)
   │  watermark incremental extract  ── Polars (Rust) read
   ▼
Iceberg BRONZE (append-only raw)            MinIO (S3 object store)
   │  Polars (Rust) dedup + clean           catalog: Lakekeeper (Rust REST)
   ▼                                         writes:  PyIceberg
Iceberg SILVER (latest-per-PK)
   │  Polars (Rust) joins + aggregates
   ▼
Iceberg GOLD (marts) ──► Trino ──► Superset
   ▲
Airflow (LocalExecutor) orchestrates extract → silver → gold
```

| Layer | Tool | Rust? |
|-------|------|-------|
| Source | PostgreSQL (e-commerce, Faker) | — |
| Object store | MinIO (S3) | — |
| Table format | Apache Iceberg | — |
| Catalog | **Lakekeeper** (REST) | ✅ |
| Extract / transform | **Polars** | ✅ |
| Iceberg writes | PyIceberg | Python |
| Query | Trino | JVM |
| BI | Superset | Python |
| Orchestration | Airflow | Python |

**On "Rust-accelerated":** Rust is load-bearing in the catalog (Lakekeeper) and the
read/transform engine (Polars). Writes go through PyIceberg because no production
pure-Rust Iceberg *write* path exists as of 2026. Rationale + the DuckDB alternative:
[docs/poc-architecture.md](docs/poc-architecture.md).

## Prerequisites
- Docker Desktop — **≥14 GB** for the full stack; **~6–7 GB** for the MVP (no Airflow/Superset).
- Python 3.10+ on the host (seeder + manual pipeline runs); `make`.
- Image tags are pinned in `.env.example`; verify on first `docker compose pull`.

## Quickstart — MVP

```bash
make up                          # Postgres, MinIO, Lakekeeper, Trino
make smoke                       # Phase-1 acceptance: a parquet lands in MinIO
make seed-deps seed-full         # synthetic e-commerce data
make pipe-deps pipeline          # bronze -> silver -> gold (Polars + PyIceberg)
make trino-cli                   # paste bi/trino_validation_queries.sql
```

## Quickstart — Full slice (Airflow + Superset)

```bash
make demo                        # boot full, seed, full + incremental ELT
make superset-ui                 # http://localhost:8088  (admin/admin)
make airflow-ui                  # http://localhost:8082  (admin/admin)
```

## Prove incremental ingestion
```bash
make seed-append                 # new orders + bumped updated_at
make ingest-bronze               # appends ONLY the watermark delta
```
Confirm via the Iceberg `$snapshots` metadata table (`added-records`).

## Tests
```bash
make test                        # pure-Polars transform tests, no stack needed
```

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| Trino fails on first write | keep `s3.path-style-access=true` (set in `infra/trino/etc/catalog/iceberg.properties`) |
| services can't reach each other | configs use service DNS (`minio:9000`), never `localhost` |
| bucket not found | `minio-bootstrap` creates `warehouse`; check it ran |
| Lakekeeper warehouse errors | verify `infra/lakekeeper/bootstrap.sh` JSON vs running version `/swagger-ui` |
| Airflow port | UI is on **8082** (8080 = Trino) |
| OOM | run MVP (`make up`) not `up-full`; raise Docker RAM |

## Layout
```
docker-compose.yml      # all services (Airflow/Superset under `full` profile)
infra/                  # minio + lakekeeper bootstrap, trino config
source/                 # schema.sql + Faker seeder
pipeline/               # Polars/PyIceberg ELT + transforms
orchestration/          # Airflow image + DAG
bi/                     # Superset bootstrap + Trino queries
tests/                  # transform unit tests
docs/                   # architecture + demo runbook
```

Built from the plan at [../plans/260613-1035-poc-rust-lakehouse-end-to-end/](../plans/260613-1035-poc-rust-lakehouse-end-to-end/).
