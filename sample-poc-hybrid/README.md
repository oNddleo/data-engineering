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

## Phase 1 status (current)

Infrastructure docker-compose stack:
- 1 Spark master + 1 worker (2 workers in `full` profile)
- Kafka 4.0 KRaft, single combined controller+broker node (image auto-formats from `CLUSTER_ID` env var)
- MinIO with `lakehouse` bucket and medallion prefixes
- 2 Postgres instances (metastore/UC/airflow, OLTP)
- Hive Metastore 4.0 (primary catalog)
- Trino 470 with Delta connector backed by HMS
- Unity Catalog OSS (profile `uc`, experimental Spark-only)

## Quick start

```bash
make env                 # one-time .env copy
make up-hybrid           # bring stack up (UC primary)
make ps                  # status of containers
make smoke-hybrid        # spark-submit writes & reads 1 Delta row
make trino-cli           # SHOW CATALOGS / SHOW SCHEMAS FROM delta
make down-hybrid         # stop, keep volumes
make clean-hybrid        # destructive: remove volumes too
```

Experimental UC OSS (Spark only, not queryable from Trino 470):
```bash
make up-uc               # adds unity-catalog + bootstrap services
```

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

| Phase | Status |
|-------|--------|
| 1 — Infrastructure & Docker Compose | In Progress (this commit) |
| 2 — IoT & Media data generators | Pending |
| 3 — Bronze (Spark Streaming IoT) | Pending |
| 4 — Bronze (Spark batch media metadata) | Pending |
| 5 — Silver (cleansing/standardization) | Pending |
| 6 — Gold (marts + cross-domain) | Pending |
| 7 — Airflow 3.0 orchestration | Pending |
| 8 — Trino + Superset BI | Pending |
| 9 — Tests + docs | Pending |

See [`plan.md`](./plan.md) for the full plan + Validation Log.
