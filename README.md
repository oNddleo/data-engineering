# sample-poc-hybrid — Spark + Delta Lake + Kafka KRaft for IoT, Image, Video

POC mở rộng kiến trúc 7 tầng (xem [`../knowledge/architecture-layer-diagram.md`](../knowledge/architecture-layer-diagram.md)) để xử lý **IoT streaming + image + video metadata** trên một lakehouse chung dùng **Apache Spark 4.0 + Delta Lake 4.0 + Kafka 4.0 KRaft + Hive Metastore 4.0** (mô phỏng Databricks runtime trên laptop bằng `docker-compose`). Unity Catalog OSS 0.3 có sẵn ở profile `uc` cho thử nghiệm Spark-only, nhưng Trino 470 chưa support nên HMS là catalog primary.

> Stack tham chiếu nhưng *khác* `sample-poc` (Polars/Iceberg). Hai POC chạy song song được, port không trùng.

## Pinned versions

| Component | Version |
|-----------|---------|
| Apache Spark | 4.0.0 (Scala 2.13, JDK 17) |
| Delta Lake | 4.0.0 |
| Apache Kafka | 4.0.0 (KRaft single-mode, **không Zookeeper**) |
| Hive Metastore (primary) | 4.0.0 |
| Unity Catalog OSS (profile `uc`, Spark-only) | 0.3.0 |
| Trino | 470 |
| Apache Airflow | 3.0.x |
| Apache Superset | 4.1.x |
| PostgreSQL | 17 |
| MinIO | RELEASE.2025-04-22 |

## What's in the stack

| Tier | Component |
|------|-----------|
| Sources | Python IoT simulator, Pillow + ffmpeg media uploader, Postgres OLTP |
| Integration | Kafka 4.0 KRaft single node, MinIO S3 |
| Compute | Spark 4.0 master + worker (Delta + Kafka + UC + Postgres-JDBC jars baked in) |
| Catalog | Hive Metastore 4.0 (primary); Unity Catalog OSS 0.3 via `uc` profile |
| Query | Trino 470 with Delta connector |
| Orchestration | Airflow 3.0 — 3 DAGs (streaming supervisor, hourly batch, daily maintenance) |
| BI | Superset 4.1 with the `trino[sqlalchemy]` dialect |
| Tests | pytest + Delta-aware Spark fixture + testcontainers (slow marker) |

## Quick start

```bash
make env                 # one-time .env copy
make kafka-id            # paste into .env KAFKA_CLUSTER_ID
make up-hybrid           # bring stack up
make smoke-hybrid        # spark-submit writes & reads 1 Delta row
make seed-oltp           # 100 devices + 20 districts
make seed-iot RATE=100 DUR=60 &
make stream-iot-bronze
make stop-stream-iot     # SIGTERM the JVM driver, drains current batch
make seed-media COUNT=60
make batch-media-bronze
make build-silver
make build-gold
make trino-validate      # runs bi/trino_validation_queries.sql
make down-hybrid         # stop, keep volumes
make clean-hybrid        # destructive: remove volumes too
```

One-shot:
```bash
make demo-hybrid         # boots full stack, seeds, runs medallion, opens BI URLs
```

Experimental UC OSS (Spark-only — Trino 470 won't read it):
```bash
make up-uc               # adds unity-catalog + bootstrap services
```

## Tests

```bash
make test-deps           # pytest, pyspark, delta-spark, pillow
make test                # unit tests (no Docker required)
make test-slow           # integration smoke with testcontainers
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/poc-architecture.md`](docs/poc-architecture.md) | What this POC is + diagram + comparison vs `sample-poc` |
| [`docs/demo-runbook.md`](docs/demo-runbook.md) | Step-by-step end-to-end demo with expected durations |
| [`docs/7-layer-mapping.md`](docs/7-layer-mapping.md) | How each POC component maps to the 7-tier reference |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | First-run gotchas + recovery procedures |
| [`docs/decisions/`](docs/decisions/) | 4 short ADRs: Delta vs Iceberg, OSS vs Databricks, no ML, streaming-on-Airflow |
| [`plan.md`](plan.md) | 9-phase implementation plan + Validation Log + code-review history |
| [`plans/reports/`](plans/reports/) | Per-phase adversarial code-review reports |

## Repository layout

```
docker-compose.yml         # all services
.env.example               # pinned versions, ports, creds
Makefile                   # up/down/smoke/trino-cli/...
infra/
  spark/                   # Dockerfile (Delta 4 + Kafka 4 + UC + S3a jars)
  kafka/                   # KRaft format + topic init
  unity-catalog/           # server.properties + catalog bootstrap
  hive-metastore/          # fallback Hive 4.0 + S3a + Postgres JDBC
  minio/                   # bucket + prefix bootstrap
  postgres/                # init-meta.sql (3 DBs on one instance)
  trino/etc/               # node/config/jvm + catalog/delta.properties
plan.md + phase-*.md       # implementation roadmap (9 phases)
```

## Roadmap

All 9 phases shipped. See [`plan.md`](./plan.md) for the full plan, Validation Log, and code-review history.
