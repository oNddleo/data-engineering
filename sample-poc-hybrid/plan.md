---
title: 'Hybrid Lakehouse POC - Databricks/Spark + Delta Lake for IoT, Image, Video'
description: >-
  Extend the 7-layer architecture with Apache Spark + Delta Lake
  (Databricks-style) to ingest IoT streams via Kafka and image/video metadata
  from MinIO. Reproducible on a laptop via docker-compose.
status: pending
priority: P2
branch: feat/databricks
tags:
  - databricks
  - spark
  - delta-lake
  - kafka
  - iot
  - multimedia
  - lakehouse
  - poc
blockedBy: []
blocks: []
created: '2026-06-19T05:11:11.566Z'
createdBy: 'ck:plan'
source: skill
---

# Hybrid Lakehouse POC - Databricks/Spark + Delta Lake for IoT, Image, Video

## Overview

POC chứng minh kiến trúc 7 tầng (`knowledge/architecture-layer-diagram.md`) có thể được mở rộng để xử lý 3 loại dữ liệu mới: **IoT streaming**, **image**, **video** — dùng **Apache Spark (OSS, mô phỏng Databricks)** + **Delta Lake** thay vì stack Polars/Iceberg của `sample-poc`. Toàn bộ stack chạy bằng `docker-compose` trên laptop.

**Decisions đã chốt:**
- Deployment: OSS **Spark 4.0** + **Delta Lake 4.0** local (mô phỏng Databricks runtime).
- Table format: Delta Lake 4.0 (ACID, streaming-friendly, time travel, deletion vectors mặc định).
- IoT ingest: simulator → **Kafka 4.0 KRaft** (không Zookeeper) → Spark Structured Streaming → Delta Bronze.
- Media: lưu binary trong MinIO, Spark batch trích xuất metadata (EXIF, ffprobe) + thumbnail vào Delta. **Không có ML inference** trong POC.
- BI: **Trino 470** đọc Delta qua **Unity Catalog OSS 0.3** (ưu tiên) hoặc Hive Metastore 4.0 fallback → **Superset 4.1**.
- Orchestration: **Apache Airflow 3.0** (task SDK + dataset-aware scheduling).
- Runtime: **Python 3.12**, **PostgreSQL 17**, MinIO latest LTS.

**Pinned versions** (`.env.example`):

| Component | Version | Ghi chú |
|-----------|---------|---------|
| Apache Spark | 4.0.0 | Scala 2.13, JDK 17 |
| Delta Lake | 4.0.0 | `delta-spark_2.13:4.0.0` |
| Apache Kafka | 4.0.0 | KRaft single-mode (combined controller+broker) |
| Apache Airflow | 3.0.x | Task SDK, providers >= 3.0 |
| Trino | 470 | Delta connector |
| Apache Superset | 4.1.x | Trino driver `trino-python-client` |
| Unity Catalog OSS | 0.3.x | thay Hive Metastore khi khả thi |
| Hive Metastore | 4.0.0 | dùng nếu Unity Catalog block by Trino version |
| PostgreSQL | 17 | metastore + OLTP |
| MinIO | RELEASE.2025-xx-xx | S3 store |
| Python | 3.12 | tất cả script + Airflow + Superset |

**Out of scope:** EDMS, real CDC, ML/AI inference, multi-tenant security, production-grade Kafka HA, real cloud deployment.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Infrastructure & Docker Compose](./phase-01-infrastructure-docker-compose.md) | Completed |
| 2 | [IoT & Media Data Generators](./phase-02-iot-media-data-generators.md) | Completed |
| 3 | [Bronze - Spark Structured Streaming IoT](./phase-03-bronze-spark-structured-streaming-iot.md) | Pending |
| 4 | [Bronze - Spark Batch Image/Video Metadata](./phase-04-bronze-spark-batch-image-video-metadata.md) | Pending |
| 5 | [Silver - Cleansing & Standardization](./phase-05-silver-cleansing-standardization.md) | Pending |
| 6 | [Gold - Marts & Cross-Domain Aggregates](./phase-06-gold-marts-cross-domain-aggregates.md) | Pending |
| 7 | [Orchestration with Airflow](./phase-07-orchestration-with-airflow.md) | Pending |
| 8 | [Query & BI (Trino + Superset)](./phase-08-query-bi-trino-superset.md) | Pending |
| 9 | [Tests & Documentation](./phase-09-tests-documentation.md) | Pending |

## Architecture Mapping (sang 7-layer)

| Layer | Component POC | Tool |
|-------|---------------|------|
| L1 Source | IoT simulator, image/video uploader, Postgres devices | Python, Faker, MinIO |
| L2 Integration | Kafka + Kafka Connect (event), boto3 ingest (file) | Kafka, MQTT-Kafka bridge |
| L3 Lakehouse | Delta Lake on MinIO, Spark compute, Trino query | Spark 4.0, Delta 4.0, Trino 470 |
| L4 Governance | Delta schema enforcement, Great Expectations (Phase 9) | Delta constraints, GE |
| L5 EDMS | (out of scope) | — |
| L6 Security | MinIO IAM (basic), Keycloak (optional) | MinIO policies |
| L7 Presentation | Superset dashboards | Superset |

## Dependencies

- Cross-plan: Plan kế thừa pattern từ `plans/260613-1035-poc-rust-lakehouse-end-to-end/` (cùng cấu trúc bronze/silver/gold + orchestrate Airflow + BI Superset).
- Không block plan hiện hữu nào; chạy song song với `sample-poc` (port khác).

## Validation Log

### Session 1 — 2026-06-19

**Q1 — Version risk stack (Spark 4.0 / Delta 4.0 / UC OSS 0.3):**
Decision → giữ pin mới nhất, fallback HMS 4.0 khi UC OSS fail (docker-compose profile `hms`).
Affects: `phase-01` (đã sẵn 2 path, không cần sửa).

**Q2 — Airflow 3.0 streaming supervisor anti-pattern:**
Decision → giữ DAG long-running + retry 3x cho POC. Document ADR `docs/decisions/004-streaming-on-airflow-poc-accepted-tradeoff.md`.
Affects: `phase-07` (giữ nguyên), `phase-09` (thêm ADR 004 vào docs/decisions/).

**Q3 — Maintenance OPTIMIZE/VACUUM vs streaming write concurrent:**
Decision → DAG 3 maintenance pause DAG 1 streaming trước khi OPTIMIZE/VACUUM, restart sau khi xong (sequential safe).
Affects: `phase-07` (cập nhật DAG 3 thêm task `pause_streaming` + `resume_streaming` bookend), `phase-05` (chú thích OPTIMIZE chạy trong maintenance window).

**Q4 — Test scope Phase 9:**
Decision → Unit test only + 1 smoke integration test bằng testcontainers (Kafka + MinIO ephemeral). Marker `slow` để dev opt-in.
Affects: `phase-09` (đã match, không cần sửa).

### Session 2 — 2026-06-19 (post code-review of Phase 1)

Code-reviewer xác minh **Trino 470 OSS không support `delta.metastore=unity`** (chỉ Starburst + post-470 OSS). Reverse decision Q1 từ Session 1: HMS giờ là **primary catalog**, UC OSS chuyển sang profile `uc` experimental Spark-only.

Affects:
- `phase-01`: HMS thành default service (bỏ `profiles: [hms]`); UC + bootstrap thêm `profiles: [uc]`; Trino delta.properties dùng `hive.metastore=thrift`.
- `phase-03`/`phase-04`/`phase-05`/`phase-06`/`phase-08`: catalog reference đổi từ `unity.hybrid.*` sang HMS schema (chỉ `bronze.*`, `silver.*`, `gold.*`). Sẽ propagate khi cook các phase đó.
- Spark config: `spark.sql.catalogImplementation=hive` + `DeltaCatalog` wrapper thay `UCSingleCatalog`.

Code-review action items đã apply tại Phase 1:
- C1 (Trino UC support): chuyển HMS primary.
- C2 (UC path): `/opt/unitycatalog/` → `/home/unitycatalog/`.
- C3 (UC healthcheck): bash `/dev/tcp/localhost/8087`.
- C4 (Bitnami command override): bỏ `command:` ở spark-master/worker.
- H2 (Kafka format script): bỏ format-storage.sh; apache/kafka:4.0 image tự format từ `CLUSTER_ID` env.
- H4 (race condition): thêm `depends_on: minio-bootstrap: service_completed_successfully` ở HMS, spark-master, UC, Trino.
- M1 (spark-worker healthcheck): thêm curl /:8081.
- M4 (Trino healthcheck): dùng `/usr/lib/trino/bin/health-check` từ image.

### Whole-Plan Consistency Sweep

Đã re-scan `plan.md` + 9 phase files cho stale terms sau khi đổi version + KRaft:
- "Zookeeper" → 0 reference còn lại (đã thay KRaft).
- "Spark 3.5" / "3.2.0" / "_2.12" → đã thay sang 4.0.0 / _2.13 trong phase-01, phase-03, phase-07.
- "Hive Metastore only" → đã đổi sang "UC primary + HMS fallback" nhất quán giữa phase-01, phase-08, phase-03.
- "Airflow 2.x DAG API" → phase-07 cập nhật sang `airflow.sdk`.
- Không phát hiện contradiction còn tồn đọng.

## Success Criteria

- [ ] `make demo-hybrid` boot toàn bộ stack từ zero, end-to-end < 10 phút.
- [ ] Streaming job ingest ≥ 100 IoT events/giây bền vững trong 5 phút, không restart.
- [ ] Image (≥ 50 PNG/JPG) + Video (≥ 10 MP4) được catalog vào Delta với thumbnail.
- [ ] Superset hiển thị 3 dashboard: IoT real-time gauge, device health, media storage usage.
- [ ] Tất cả unit test transform pass; smoke test xác nhận data lineage bronze→silver→gold.
