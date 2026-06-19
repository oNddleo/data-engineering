# POC Architecture — Hybrid Lakehouse for IoT + Image + Video

A thin **vertical slice** of the enterprise 7-layer architecture in [../../knowledge/architecture-layer-diagram.md](../../knowledge/architecture-layer-diagram.md), specialised for three new payload classes: IoT telemetry, images, and videos. The goal is to prove they can share one lakehouse table format, one compute engine, and one federated query path — reproducibly via `docker-compose` on a laptop.

## Pipeline

```mermaid
flowchart TB
  subgraph L1["Sources"]
    sim[IoT simulator<br/>Python]
    media[Media uploader<br/>Pillow + ffmpeg]
    oltp[(Postgres OLTP<br/>devices + locations)]
  end

  subgraph L2["Integration"]
    kafka[(Kafka 4.0 KRaft<br/>iot.sensors)]
    minio[(MinIO S3<br/>raw-media/)]
  end

  subgraph L3["Lakehouse — Spark 4.0 + Delta 4.0"]
    bronze_iot[(bronze.iot_events<br/>append-only stream)]
    bronze_media[(bronze.media_objects<br/>batch metadata)]
    silver_iot[(silver.iot_readings<br/>dedup + 3σ flag + enrichment)]
    silver_anom[(silver.iot_anomalies)]
    silver_media[(silver.media_catalog)]
    gold_hourly[(gold.iot_hourly_metrics)]
    gold_health[(gold.device_health)]
    gold_storage[(gold.media_storage_daily)]
    gold_corr[(gold.iot_media_correlation)]
  end

  subgraph L4["Governance"]
    hms[Hive Metastore 4.0]
    delta_cdf[Delta CDF + columnMapping]
  end

  subgraph L7["Presentation"]
    trino[Trino 470]
    superset[Superset 4.1]
  end

  subgraph Orch["Orchestration"]
    airflow[Airflow 3.0<br/>3 DAGs]
  end

  sim --> kafka --> bronze_iot
  media --> minio --> bronze_media
  oltp -->|JDBC broadcast| silver_iot
  oltp -->|JDBC broadcast| silver_media
  bronze_iot --> silver_iot --> silver_anom
  bronze_media --> silver_media
  silver_iot --> gold_hourly
  silver_iot --> gold_health
  silver_media --> gold_storage
  silver_iot --> gold_corr
  silver_media --> gold_corr
  gold_hourly --> trino --> superset
  gold_health --> trino
  gold_corr --> trino
  gold_storage --> trino
  bronze_iot -. metadata .-> hms
  silver_iot -. metadata .-> hms
  airflow -. orchestrates .-> bronze_media
  airflow -. orchestrates .-> silver_iot
  airflow -. orchestrates .-> gold_hourly
```

## sample-poc vs sample-poc-hybrid

| Aspect | `sample-poc` (Rust-accelerated) | `sample-poc-hybrid` (Spark/Delta) |
|--------|--------------------------------|------------------------------------|
| Compute engine | Polars (Rust) | Apache Spark 4.0 (Scala/JVM) |
| Table format | Apache Iceberg | Delta Lake 4.0 |
| Catalog | Lakekeeper (Rust) | Hive Metastore 4.0 (UC OSS profile available) |
| Streaming | — (batch only) | Spark Structured Streaming on Kafka 4.0 KRaft |
| Payloads | OLTP e-commerce | IoT + image + video |
| ML extension hook | — | Out-of-scope for POC; deferred to plan |
| Airflow | LocalExecutor (2.x style) | LocalExecutor (Airflow 3.0 task SDK) |
| BI | Superset (Iceberg via Trino) | Superset (Delta via Trino) |

## What's intentionally out of scope

- EDMS layer (L5) — no Mayan/Alfresco integration.
- Real CDC from operational sources — synthetic OLTP via Faker is enough.
- ML inference (YOLO/Whisper) on images/videos — see `decisions/003-no-ml-inference-in-poc.md`.
- Multi-tenant security, Keycloak SSO, Ranger row/column policies.
- Production-grade Kafka HA — single combined-mode KRaft node.
- Cloud deployment — bake-off targets the laptop.

## Sources of truth

- Plan: [`../plan.md`](../plan.md) — 9 phases, Validation Log, code-review history.
- Code-review reports: [`../plans/reports/`](../plans/reports/) — per-phase adversarial reviews.
