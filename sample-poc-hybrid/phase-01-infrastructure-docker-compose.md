---
phase: 1
title: Infrastructure & Docker Compose
status: completed
priority: P1
effort: 1d
dependencies: []
---

# Phase 1: Infrastructure & Docker Compose

## Overview

Dựng nền tảng `docker-compose` chạy local mô phỏng Databricks: Spark 4.0 master + 2 workers (Delta Lake 4.0 jars pre-installed), **Kafka 4.0 KRaft** (không Zookeeper), MinIO (S3 store), Postgres 17 (catalog + OLTP source), **Unity Catalog OSS 0.3** (primary catalog) hoặc Hive Metastore 4.0 fallback, Airflow 3.0, Superset 4.1, Trino 470. Một stack duy nhất, profile `mvp` / `full`.

## Requirements

- **Functional**: tất cả container start healthy với `make up-hybrid`, cùng network `hybrid-net`, không trùng port với `sample-poc` (8080/8082/8088).
- **Non-functional**: tổng RAM yêu cầu ≤ 12 GB; image pin version cụ thể trong `.env.example`.

## Architecture

```
hybrid-net (docker bridge)
├── spark-master (8081 UI, 7077 master)            [bitnami/spark:4.0.0]
├── spark-worker-1, spark-worker-2                 [bitnami/spark:4.0.0]
├── kafka (9092 client, 9093 controller)           [apache/kafka:4.0.0 — KRaft combined mode]
├── kafka-ui (8090, optional)                      [provectuslabs/kafka-ui:latest]
├── minio (9001 console, 9000 API)                 [minio/minio:RELEASE.2025-xx-xx]
├── minio-bootstrap (one-shot)                     [minio/mc:latest]
├── postgres-meta (5433)                           [postgres:17-alpine] — UC backend + airflow db
├── postgres-oltp (5434)                           [postgres:17-alpine] — devices source
├── unity-catalog (8087)                           [unitycatalog/unitycatalog:0.3.0]
│   └── (fallback) hive-metastore (9083)           [apache/hive:4.0.0]
├── trino (8085)                                   [trinodb/trino:470] — Delta connector
├── airflow-apiserver (8086) + scheduler + dag-processor   [apache/airflow:3.0.x]
└── superset (8089)                                [apache/superset:4.1.x]
```

> **Kafka KRaft note**: Apache Kafka 4.0 loại bỏ hoàn toàn Zookeeper; container chạy `process.roles=controller,broker` (combined mode cho POC). Cluster ID sinh bằng `kafka-storage random-uuid` ở init container và mount qua volume `kafka-data`.

Spark image custom build (`infra/spark/Dockerfile`) base `bitnami/spark:4.0.0` (JDK 17, Scala 2.13) gồm: `delta-spark_2.13:4.0.0`, `delta-storage:4.0.0`, `spark-sql-kafka-0-10_2.13:4.0.0`, `kafka-clients:4.0.0`, `hadoop-aws:3.4.1`, `aws-java-sdk-bundle:1.12.x`, `unitycatalog-spark:0.3.0` (UC client); copy `spark-defaults.conf` set `spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension`, `spark.sql.catalog.unity=io.unitycatalog.spark.UCSingleCatalog`, S3a endpoint = `http://minio:9000`, path-style true.

## Related Code Files

- Create: `docker-compose.yml`, `.env.example`, `Makefile`
- Create: `infra/spark/Dockerfile`, `infra/spark/spark-defaults.conf`, `infra/spark/log4j2.properties`
- Create: `infra/minio/bootstrap.sh` (tạo bucket `lakehouse`, policy public-read cho `thumbnails/`)
- Create: `infra/unity-catalog/Dockerfile`, `infra/unity-catalog/server.properties`, `infra/unity-catalog/bootstrap-catalogs.sh` (tạo catalog `hybrid`, schema `bronze/silver/gold`)
- Create: `infra/hive-metastore/Dockerfile`, `infra/hive-metastore/metastore-site.xml` (fallback path nếu Trino 470 chưa stable với UC OSS)
- Create: `infra/trino/etc/catalog/delta.properties` (Delta connector — `metastore=unity` hoặc `metastore=thrift` cho HMS)
- Create: `infra/kafka/Dockerfile` (base `apache/kafka:4.0.0`), `infra/kafka/server.properties` (KRaft), `infra/kafka/format-storage.sh` (`kafka-storage format -t $CLUSTER_ID -c server.properties`), `infra/kafka/create-topics.sh` (`iot.sensors`, `iot.sensors.dlq`)
- Create: `infra/airflow/Dockerfile` (base `apache/airflow:3.0.x` + `apache-airflow-providers-apache-spark>=5.0`, `apache-airflow-providers-cncf-kubernetes` optional)

## Implementation Steps

1. Khởi tạo `docker-compose.yml` với `services:` cho từng component, healthcheck đầy đủ; map volume named cho `minio-data`, `pg-meta-data`, `pg-oltp-data`, `kafka-data`, `uc-data`.
2. Build Spark image: copy jar Delta 4.0 + S3 + Kafka 4.0 + Unity Catalog client vào `$SPARK_HOME/jars`; ENTRYPOINT `start-master.sh` hoặc `start-worker.sh` theo arg.
3. Bootstrap MinIO: container `minio-bootstrap` chạy `mc alias` + `mc mb lakehouse` + tạo subprefix `bronze/`, `silver/`, `gold/`, `raw-media/`, `thumbnails/`, `_checkpoints/`.
4. **Kafka KRaft init** (one-shot container):
   - Sinh `CLUSTER_ID = $(kafka-storage random-uuid)`, lưu vào volume.
   - `kafka-storage format -t $CLUSTER_ID -c /etc/kafka/server.properties --ignore-formatted`.
   - Kafka container chạy với `KAFKA_PROCESS_ROLES=controller,broker`, `KAFKA_NODE_ID=1`, `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093`, `KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093`, `KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT`, `KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER`.
5. **Unity Catalog OSS**: chạy `uc-server` (Java 17, port 8087); chạy script bootstrap tạo catalog `hybrid`, schema `bronze/silver/gold` qua UC CLI `bin/uc catalog create --name hybrid`.
6. **Hive Metastore fallback**: dùng image `apache/hive:4.0.0`; init schema (`schematool -initSchema -dbType postgres -url jdbc:postgresql://postgres-meta:5432/metastore`). Chỉ enable khi compose profile `hms`.
7. Trino: `delta.properties` ưu tiên `unity-catalog`, format:
   ```
   connector.name=delta_lake
   delta.metastore=unity
   delta.unity-catalog.uri=http://unity-catalog:8087
   hive.s3.endpoint=http://minio:9000
   hive.s3.path-style-access=true
   ```
8. Kafka tạo 2 topic (replication-factor=1, partitions=3) qua container `kafka-init` chạy `kafka-topics.sh --bootstrap-server kafka:9092 --create ...`.
9. Makefile target: `up-hybrid`, `down-hybrid`, `logs`, `smoke-hybrid` (spark-submit job in 1 row vào Delta qua UC).

## Success Criteria

- [ ] `docker compose up -d` không lỗi, tất cả service healthy ≤ 120s (UC + HMS init lâu hơn Zookeeper-Kafka cũ).
- [ ] `make smoke-hybrid` viết 1 row Delta vào `s3a://lakehouse/bronze/_smoke/` qua UC catalog rồi đọc lại pass.
- [ ] Trino `SHOW CATALOGS` thấy `delta`; `SHOW SCHEMAS FROM delta` trả về `bronze, silver, gold`.
- [ ] Kafka topic `iot.sensors` tồn tại, `kafka-console-producer.sh --bootstrap-server kafka:9092` send được message.
- [ ] `kafka-metadata-quorum.sh describe --status` xác nhận KRaft controller quorum healthy (1 voter).

## Risk Assessment

- **OOM khi chạy 2 spark workers**: mitigate bằng cách đặt `SPARK_WORKER_MEMORY=2G` cho POC, phép user chỉnh trong `.env`.
- **Trino 470 ↔ Unity Catalog OSS 0.3 chưa đầy đủ feature**: nếu Delta connector của Trino chưa support UC ở version pin, fallback HMS bằng `--profile hms` ở docker-compose, đổi `delta.metastore=thrift` — đã chuẩn bị sẵn cả 2 path.
- **Kafka KRaft single-node không HA**: chấp nhận cho POC; sản xuất cần ≥ 3 controller.
- **Spark 4.0 đổi default Scala 2.13**: tất cả jar phải `_2.13`; double-check không pull nhầm `_2.12`.
- **Airflow 3.0 task SDK khác 2.x**: DAG cần migrate sang `airflow.sdk` import; xem phase 7.
- **Port conflict với sample-poc**: tất cả port hybrid offset +5 (8085, 8086, 8087, 8089...).
