# Codebase Summary — Hybrid Lakehouse POC

Quick reference for navigating the ~6,400 LOC of this Spark 4.0 + Delta Lake 4.0 + Kafka 4.0 POC.

## Directory Tree

```
sample-poc-hybrid/
├── docker-compose.yml              All services; profiles: mvp (default), uc, hms, airflow, bi, full
├── .env.example                    Pinned image tags, ports, MinIO/Postgres creds
├── Makefile                        help, up-hybrid, demo-hybrid, seed-*, stream-*, build-*, test-*
├── pytest.ini                      Pytest markers (slow)
├── README.md                       Quick start, tests, docs index
├── plan.md                         9-phase implementation plan + Validation Log
├── phase-*.md                      Per-phase specs (9 files)
├── CLAUDE.md                       Project AI assistant instructions
│
├── infra/                          Infrastructure & service configurations
│   ├── spark/                      Bitnami Spark 4.0 image + Delta 4 + Kafka 4 + UC + S3a
│   │   ├── Dockerfile             (custom JAR layers: Delta, UC client, hadoop-aws, Postgres JDBC, pillow/boto3)
│   │   ├── spark-defaults.conf     Hive support, S3a warehouse, executorEnv PYTHONPATH
│   │   ├── log4j2.properties       Info level, roll by size
│   │   └── scripts/smoke-test.py   One-liner Delta write+read validation
│   ├── kafka/                      KRaft format (no Zookeeper), topic bootstrap
│   │   └── create-topics.sh        (via CLUSTER_ID env; auto-format)
│   ├── minio/                      S3-compatible object store
│   │   └── bootstrap.sh            Create lakehouse bucket + medallion prefixes
│   ├── postgres/                   Metastore backend + OLTP + Airflow + Superset DBs
│   │   └── init-meta.sql           (3 schemas: metastore, airflow, superset)
│   ├── unity-catalog/              UC OSS 0.3 (profile: uc only)
│   │   └── server.properties, bootstrap-catalogs.sh
│   ├── hive-metastore/             Hive 4.0 + Postgres JDBC + hadoop-aws (primary catalog)
│   │   ├── Dockerfile             (custom image, not OS-provided)
│   │   └── metastore-site.xml      S3a warehouse, Postgres backend, auto-schema
│   ├── trino/etc/                  Trino 470 (Delta connector via Thrift HMS)
│   │   ├── config.properties, node.properties, jvm.config
│   │   └── catalog/delta.properties (hive.metastore=thrift)
│   ├── superset/                   Apache Superset 4.1 + trino[sqlalchemy] dialect
│   │   └── Dockerfile             (custom image, pinned driver)
│   ├── airflow/                    Apache Airflow 3.0 LocalExecutor (profile: airflow, full)
│   │   ├── Dockerfile             (docker CLI + providers)
│   │   └── requirements.txt        (apache-spark, docker, postgres, airflow 3.0.6+)
│   └── [service configs]           healthchecks, depends_on, port mappings
│
├── source/                         (Phase 2) Data generators on host
│   ├── iot-simulator.py            ~100 device pool, 4 sensors, confluent-kafka → Kafka topic
│   ├── media-uploader.py           Pillow PNG/JPG + ffmpeg MP4 → MinIO raw-media/
│   ├── seed-oltp.py                Faker(vi_VN) + Postgres INSERT — 100 devices, 20 Hanoi districts
│   ├── schema-oltp.sql             DDL for devices, locations, device_config tables
│   ├── requirements.txt            (confluent-kafka 2.5, boto3 1.34, pillow 10.4, piexif 1.1.3, faker 30)
│   └── schemas/
│       ├── iot-event.schema.json   Event ID (ULID), device, sensor, timestamp, value, unit
│       └── media-object.schema.json Object key, MIME type, size, etag
│
├── pipeline/                       (Phases 3–6) Spark batch & streaming jobs
│   ├── spark_jobs/
│   │   ├── streaming-iot-bronze.py    [Phase 3] Kafka → Delta via foreachBatch (idempotent txnAppId)
│   │   ├── batch-media-bronze.py      [Phase 4] S3 scan + anti-join + Python UDF extract EXIF/ffprobe
│   │   ├── build-silver-iot.py        [Phase 5] Dedup by event_id, 3σ outlier flag, MERGE INTO
│   │   ├── build-silver-media.py      [Phase 5] Dedup by object_key, dim broadcast, MERGE INTO
│   │   ├── maintenance-optimize.py    [Phases 5/7] OPTIMIZE + ZORDER + VACUUM RETAIN 168h
│   │   ├── build-gold-iot-hourly.py   [Phase 6] avg/min/max + percentile_approx(0.95)
│   │   ├── build-gold-device-health.py [Phase 6] last_seen/lag/anomaly_rate (OVERWRITE)
│   │   ├── build-gold-media-storage.py  [Phase 6] daily file_count + bytes + top_device breakdown
│   │   ├── build-gold-iot-media-correlation.py [Phase 6] ±300s range join + row_number(1)
│   │   └── lib/
│   │       ├── spark_session.py       build_streaming_session() factory
│   │       ├── iot_schema.py          JSON → PySpark StructType for bronze.iot_events
│   │       ├── media_extractors.py    extract_exif(), extract_ffprobe(), make_thumbnail()
│   │       ├── dlq_writer.py          DLQ for parse failures (separate Delta table)
│   │       ├── dim_loader.py          load_dim_broadcast() → Postgres JDBC + caching
│   │       └── unit_normalizer.py     per-sensor unit conversions (Celsius→Fahrenheit, etc.)
│   │
│   └── conf/                       (JSON-compatible YAML, no PyYAML dep)
│       ├── streaming-iot-bronze.yaml  bootstrap_servers, source_topic, delta_path, checkpoint_path
│       ├── batch-media-bronze.yaml    scan_path, dlq_topic, delta_path, output_path
│       ├── build-silver-iot.yaml      bronze_table, dim_table, silver_table, anomaly_path
│       ├── build-silver-media.yaml    bronze_table, silver_table, archive_path
│       ├── build-gold-iot-hourly.yaml silver_table, gold_table
│       ├── build-gold-device-health.yaml silver_table, gold_table
│       ├── build-gold-media-storage.yaml silver_table, gold_table
│       ├── build-gold-iot-media-correlation.yaml silver_iot, silver_media, gold_table
│       └── maintenance-optimize.yaml  targets (by schema.table), retention_hours, parallel_jobs
│
├── orchestration/                  (Phase 7) Airflow 3.0 DAGs
│   ├── Dockerfile                 apache/airflow:3.0.6 + docker CLI + providers
│   ├── requirements.txt            (providers: apache-spark, docker, postgres ≥ 3.0)
│   └── dags/
│       ├── lib/spark_submit_defaults.py     docker exec + spark-submit cmd builder
│       ├── streaming_iot_bronze_supervisor.py   [DAG 1] schedule=None, retries=3 exp backoff → long-running
│       ├── hybrid_batch_pipeline.py             [DAG 2] schedule=@hourly, fan-out media_bronze→silver_media, silver_iot→gold_*
│       └── maintenance_daily.py                 [DAG 3] schedule="0 2 * * *" → pause stream → OPTIMIZE → resume
│
├── bi/                             (Phase 8) Query validation & BI seeding
│   ├── trino_validation_queries.sql   Catalog/schema wiring, bronze counts, silver dedup proof, outlier rate, gold snapshots
│   └── superset/
│       └── bootstrap.sh           Idempotent: db upgrade + create admin + Trino connection via `superset shell`
│
├── tests/                          (Phase 9) pytest fixtures, unit & integration tests
│   ├── conftest.py                Delta-aware Spark fixture (module-scoped), slow marker skip config
│   ├── requirements.txt            pytest 8.3, pyspark 4.0, delta-spark 4.0, chispa, pillow, testcontainers 4.8
│   ├── unit/
│   │   ├── test_unit_normalizer.py       9 parametrized sensor unit conversions
│   │   ├── test_media_extractors.py      EXIF round-trip, PNG-no-EXIF, thumbnail magic, ffprobe-missing
│   │   └── test_spark_pipeline_units.py  PERMISSIVE parse, 3σ outlier flag, MERGE idempotency
│   └── integration/
│       └── test_smoke_streaming.py       testcontainers Kafka + Spark.AvailableNow → Delta count == 10
│
├── quality/great_expectations/      (scaffolded, empty — GE suites in v2 roadmap)
│
├── docs/                            Core documentation (this directory)
│   ├── project-overview-pdr.md      Problem, scope, success criteria, stakeholders
│   ├── codebase-summary.md          (this file) — layout guide + per-directory purpose
│   ├── code-standards.md            Naming convention, YAML format, idempotency, MERGE strategy
│   ├── system-architecture.md       Mermaid diagram, bronze→silver→gold contract
│   ├── deployment-guide.md          Local-only: prerequisites, step-by-step, profiles, reset playbook
│   ├── design-guidelines.md         Superset dashboard conventions, file naming policy
│   ├── poc-architecture.md          (EXISTING) What + diagram + vs sample-poc
│   ├── demo-runbook.md              (EXISTING) Step-by-step with durations
│   ├── 7-layer-mapping.md           (EXISTING) Component ↔ reference layer mapping
│   ├── troubleshooting.md           (EXISTING) First-run gotchas, recovery procedures
│   └── decisions/
│       ├── 001-delta-vs-iceberg.md  Databricks alignment, CDF, coexistence with sample-poc
│       ├── 002-oss-spark-vs-databricks.md  Local Kafka + MinIO unreachable from Databricks CE
│       ├── 003-no-ml-inference-in-poc.md   Model serving deferred; bronze stores binary + thumbnail
│       └── 004-streaming-on-airflow-poc-accepted-tradeoff.md  K8s/Databricks Job for production
│
├── plans/                          Implementation planning
│   ├── plan.md                     (link at root) 9-phase overview, Validation Log
│   ├── phase-01..09-*.md          (links at root) Per-phase specs
│   └── reports/
│       ├── reviewer-2026-06-19-phase-01-*.md      Code-review adversarial (CRITICAL/HIGH items)
│       ├── reviewer-2026-06-19-phase-{02,03,04-06,07-09}-*.md  Consolidated reviews
│       └── [others from sibling plan 260613-1035]  Reference reviews
│
└── .gitignore, LICENSE, etc.       Standard repo metadata
```

## Entry-Point Map: Where to Start for Each Task

| Task | Entry File(s) | Purpose | Phase |
|------|----------------|---------|-------|
| **Boot the stack** | `docker-compose.yml`, `Makefile` | `make env` → `make kafka-id` → `make up-hybrid` | 1 |
| **Seed OLTP** | `source/seed-oltp.py` | Create 100 devices, 20 locations in Postgres | 2 |
| **Seed IoT stream** | `source/iot-simulator.py` | Generator loop: produce to Kafka topic | 2 |
| **Ingest IoT bronze** | `pipeline/spark_jobs/streaming-iot-bronze.py` + config | Kafka → Delta, foreachBatch idempotency | 3 |
| **Seed media** | `source/media-uploader.py` | Generate PNG/JPG/MP4 to MinIO raw-media/ | 2 |
| **Ingest media bronze** | `pipeline/spark_jobs/batch-media-bronze.py` + config | S3 scan → extract EXIF/ffprobe → thumbnail | 4 |
| **Cleanse IoT silver** | `pipeline/spark_jobs/build-silver-iot.py` + config | Dedup, 3σ outlier, dim broadcast, MERGE | 5 |
| **Cleanse media silver** | `pipeline/spark_jobs/build-silver-media.py` + config | Dedup, dim broadcast, MERGE | 5 |
| **Build IoT marts** | `pipeline/spark_jobs/build-gold-iot-hourly.py` + config | Hourly aggregate (avg, percentile) | 6 |
| **Build device health** | `pipeline/spark_jobs/build-gold-device-health.py` + config | Device status snapshot (OVERWRITE) | 6 |
| **Build media storage** | `pipeline/spark_jobs/build-gold-media-storage.yaml.py` + config | Daily file count + storage breakdown | 6 |
| **Orchestrate batch** | `orchestration/dags/hybrid_batch_pipeline.py` | Airflow @hourly DAG, fan-out silver→gold | 7 |
| **Maintain tables** | `orchestration/dags/maintenance_daily.py` | Pause stream → OPTIMIZE → resume | 7 |
| **Query with Trino** | `bi/trino_validation_queries.sql` | Bronze counts, silver dedup proof, gold snapshots | 8 |
| **Dashboard with Superset** | `bi/superset/bootstrap.sh` | Create admin, Trino connection, run 3 dashboards | 8 |
| **Unit test transforms** | `tests/unit/test_spark_pipeline_units.py` | PERMISSIVE parse, 3σ outlier, MERGE | 9 |
| **Smoke test streaming** | `tests/integration/test_smoke_streaming.py` | testcontainers Kafka + Spark.AvailableNow | 9 |

## Data Flow: Bronze → Silver → Gold

### IoT Branch

```
Kafka (iot.sensors)
  ↓ [streaming-iot-bronze.py — foreachBatch, txnAppId+txnVersion idempotent]
bronze.iot_events (append-only, with ingestion_ts + invalid_records)
  ↓ [build-silver-iot.py — row_number(1) dedup, 3σ outlier flag, dim broadcast]
silver.iot_readings (deduplicated, enriched, anomaly_rate appended to silver.iot_anomalies)
  ├→ [build-gold-iot-hourly.py] gold.iot_hourly_metrics (avg, min, max, percentile_approx(0.95))
  ├→ [build-gold-device-health.py] gold.device_health (last_seen, lag, anomaly_rate — OVERWRITE)
  └→ [build-gold-iot-media-correlation.py] gold.iot_media_correlation (±300s range join with media)
      ↓
    Trino → Superset (3 dashboards: real-time gauge, device health, correlation)
```

### Media Branch

```
MinIO (raw-media/)
  ↓ [batch-media-bronze.py — binaryFile scan, anti-join on (object_key, etag)]
bronze.media_objects (with EXIF/ffprobe metadata + thumbnail path)
  ↓ [build-silver-media.py — row_number(1) dedup, dim broadcast]
silver.media_catalog (deduplicated, enriched)
  ├→ [build-gold-media-storage.py] gold.media_storage_daily (file_count, bytes, top_device breakdown)
  └→ [build-gold-iot-media-correlation.py] gold.iot_media_correlation (±300s range join with IoT)
      ↓
    Trino → Superset (media storage usage dashboard)
```

### Medallion Idempotency Contract

| Layer | Table | Partition | Idempotency Strategy | Update Mechanism |
|-------|-------|-----------|----------------------|------------------|
| **Bronze** | iot_events | event_date | txnAppId + txnVersion = batch_id (Spark Streaming foreachBatch) | Append (DLQ for failures) |
| **Bronze** | media_objects | ingestion_date | Anti-join on (object_key, etag = date_format(modtime) + '-' + length) | Append (rewrites get new etag) |
| **Silver** | iot_readings | event_date | MERGE when_matched_update condition="s.ingestion_ts > t.ingestion_ts" | MERGE INTO |
| **Silver** | media_catalog | ingestion_date | MERGE when_matched_update condition="s.ingestion_ts > t.ingestion_ts" | MERGE INTO |
| **Gold** | iot_hourly_metrics | metric_date + hour | MERGE on (device_id, sensor_id, hour) | MERGE INTO |
| **Gold** | device_health | health_date | OVERWRITE (no merge needed; snapshot is tiny) | OVERWRITE |
| **Gold** | media_storage_daily | storage_date | OVERWRITE (daily snapshot) | OVERWRITE |
| **Gold** | iot_media_correlation | corr_date | OVERWRITE (daily snapshot) | OVERWRITE |

## Configuration Files (JSON-Compatible YAML)

All `pipeline/conf/*.yaml` files are **JSON-compatible** (no PyYAML-specific syntax). They can be parsed by:
- Pure Python json library (after YAML→JSON conversion).
- Bash jq + yq (on-the-fly).
- Spark SQL (via `from_json()`).

**Example:** `pipeline/conf/streaming-iot-bronze.yaml`
```json
{
  "bootstrap_servers": "kafka:9092",
  "source_topic": "iot.sensors",
  "delta_path": "s3a://lakehouse/bronze/iot_events",
  "checkpoint_path": "s3a://lakehouse/_checkpoints/bronze_iot_events"
}
```

This eliminates a `PyYAML` runtime dependency in Spark containers.

## Module Organization

### `pipeline/spark_jobs/lib/` — Pure-Function Libraries

Each module is **importable** (snake_case, no main block):
- `spark_session.py` — build_streaming_session() factory.
- `iot_schema.py` — JSON → PySpark StructType conversion.
- `media_extractors.py` — extract_exif(), extract_ffprobe(), make_thumbnail().
- `dlq_writer.py` — DLQ table append for parse failures.
- `dim_loader.py` — load_dim_broadcast() caches Postgres JDBC result.
- `unit_normalizer.py` — Sensor unit conversions (no-op storage, lazy broadcast).

### Entry-Point Scripts

All `pipeline/spark_jobs/*.py` are **runnable scripts** (kebab-case names, entry point at module level):
- `streaming-iot-bronze.py` — spark-submit entry; reads config, builds session, starts stream.
- `batch-media-bronze.py` — spark-submit entry; reads config, scans S3, writes Delta.
- etc.

**Naming Convention:**
- `snake_case` for importable modules (in `lib/`).
- `kebab-case` for spark-submit entry scripts (why: Airflow DAGs import them as modules; kebab-case signals "not meant to be imported").

### Airflow DAGs

All `orchestration/dags/*.py` use `snake_case` because Airflow's autodiscovery requires `importlib` to load DAG files.

## Known Limitations & Future Work

| Item | Status | v2 Plan |
|------|--------|---------|
| **Streaming Supervisor** | POC accepts Airflow restart risk | Move to K8s Deployment or Databricks Job continuous |
| **Unity Catalog** | Spark-only (profile: uc); Trino 470 blocks | Upstream to Starburst or post-470 OSS |
| **ML Inference** | Not in scope (binary + thumbnail stored) | YOLO/Whisper on bronze.media_objects |
| **Great Expectations** | Scaffolded, empty | v2 add GE suites per gold mart |
| **Multi-region** | Single KRaft node | v2 multi-region Kafka + Databricks Asset Bundles export |
| **Ranger Policies** | Not implemented | v2 add row/column security |

---

**Codebase Version:** 1.0 (All 9 phases complete) | **Last Updated:** 2026-06-19
