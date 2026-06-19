---
phase: 3
title: Bronze - Spark Structured Streaming IoT
status: completed
priority: P1
effort: 1.5d
dependencies:
  - 1
  - 2
---

# Phase 3: Bronze - Spark Structured Streaming IoT

## Overview

Spark Structured Streaming consumer Kafka `iot.sensors` → ghi append-only vào Delta Bronze trên MinIO (`s3a://lakehouse/bronze/iot_events/`). Bảo đảm **at-least-once**, có checkpoint, watermark, dead-letter cho payload xấu.

## Requirements

- **Functional**: stream xử lý ≥ 100 event/s ổn định 5 phút; restart từ checkpoint không mất event; parse fail → DLQ Kafka `iot.sensors.dlq`.
- **Non-functional**: trigger `processingTime="10 seconds"` (micro-batch); file size đầu ra ~64 MB sau OPTIMIZE phase 5.

## Architecture

```
Kafka iot.sensors
    │ readStream(format="kafka")
    ▼
parse JSON + schema enforcement   ──fail──►  iot.sensors.dlq
    │ valid rows
    ▼
add: ingestion_ts, ingest_date (partition), source_topic, source_offset, _rescued_data
    │
    ▼
writeStream → Delta s3a://lakehouse/bronze/iot_events
              checkpoint s3a://lakehouse/_checkpoints/bronze_iot
              outputMode("append")
              partitionBy("ingest_date")
```

**Bronze schema** (append-only):
- `event_id STRING`, `device_id STRING`, `sensor_type STRING`, `value DOUBLE`, `unit STRING`,
- `lat DOUBLE`, `lon DOUBLE`, `event_ts TIMESTAMP`, `fw_version STRING`,
- `ingestion_ts TIMESTAMP`, `ingest_date DATE` (partition), `kafka_offset LONG`, `kafka_partition INT`, `_rescued_data STRING`

## Related Code Files

- Create: `pipeline/spark_jobs/streaming_iot_bronze.py`
- Create: `pipeline/spark_jobs/lib/iot_schema.py` (StructType IoT event)
- Create: `pipeline/spark_jobs/lib/spark_session.py` (delta + S3a config helper)
- Create: `pipeline/spark_jobs/lib/dlq_writer.py` (foreachBatch publish DLQ qua kafka-python)
- Create: `pipeline/conf/streaming_iot_bronze.yaml` (broker, topic, checkpoint, table path)

## Implementation Steps

1. `spark_session.py` build SparkSession dùng `enableHiveSupport()` — toàn bộ Delta/Kafka/S3a/Hive config đã nằm trong `infra/spark/spark-defaults.conf` (mặc định mount vào image). Sau Session 2 validation: catalog là **HMS** (`spark.sql.catalogImplementation=hive`, `spark.hadoop.hive.metastore.uris=thrift://hive-metastore:9083`), không phải UC.
2. `streaming_iot_bronze.py`:
   - `readStream.format("kafka")` với `startingOffsets="earliest"`, `maxOffsetsPerTrigger=10000`.
   - `from_json(col("value").cast("string"), iot_schema, options={"mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_rescued_data"})`.
   - Tách 2 nhánh: valid (rescued IS NULL) → Delta; invalid → `foreachBatch` đẩy về DLQ topic.
   - Withcolumn `ingestion_ts = current_timestamp()`, `ingest_date = to_date(ingestion_ts)`.
3. `writeStream.format("delta").outputMode("append").option("checkpointLocation", ...).trigger(processingTime="10 seconds").partitionBy("ingest_date").start(table_path)`.
4. Tạo bảng external trong Hive Metastore: `CREATE SCHEMA IF NOT EXISTS bronze; CREATE TABLE IF NOT EXISTS bronze.iot_events ... USING DELTA LOCATION 's3a://lakehouse/bronze/iot_events'`. Bật `delta.enableChangeDataFeed=true`, `delta.columnMapping.mode=name`, `delta.minReaderVersion=3`, `delta.minWriterVersion=7` (deletion vectors). `ensure_bronze_table()` trong script chạy mỗi lần khởi động, idempotent.
5. CLI: `spark-submit --conf spark.streaming.stopGracefullyOnShutdown=true streaming_iot_bronze.py --config conf/...`.
6. Makefile `make stream-iot-bronze` và `make stop-stream-iot` (SIGTERM → graceful).

## Success Criteria

- [ ] Stream chạy 5 phút @ rate 100/s → bronze Delta đếm ~30,000 row.
- [ ] Inject 1 message bad JSON → xuất hiện trong `iot.sensors.dlq`, không crash stream.
- [ ] Kill spark driver, restart → checkpoint resume, không trùng + không sót event (verify qua event_id distinct count).
- [ ] Trino `SELECT count(*) FROM delta.bronze.iot_events` trả về số khớp.

## Risk Assessment

- **Checkpoint mất sync với Delta**: chỉ dùng 1 stream/1 checkpoint; document rule.
- **Schema drift (thêm field mới)**: enable `mergeSchema=true` + Delta `delta.columnMapping.mode=name` để rename-safe.
- **S3a commit chậm**: dùng `spark.sql.sources.commitProtocolClass=io.delta.sql.DeltaCommitProtocolImpl` (Delta tự xử lý).
