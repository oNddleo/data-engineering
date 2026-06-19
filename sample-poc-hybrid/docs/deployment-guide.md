# Deployment Guide — Hybrid Lakehouse POC (Local Only)

This is a **laptop-only POC**. For production migration, see [Production Considerations](#production-considerations) at the end.

## Prerequisites

**Hardware:**
- RAM: ≥ 14 GB (docker-compose runs 10+ containers).
- CPU: ≥ 4 cores recommended.
- Disk: ≥ 50 GB free (includes docker images + volumes).

**Software:**
- Docker 20.10+ with `docker compose` plugin (not standalone `docker-compose`).
- Bash 4.0+.
- `make` (or manually run commands from Makefile).
- Git (for clone + git commands in Makefile).

**Optional:**
- `jq` (JSON parsing for `make kafka-id` output).
- `curl` (manual healthchecks).
- PostgreSQL client `psql` (manual queries).

## Step-by-Step Setup

### 1. Clone & Initialize Environment

```bash
# Clone the repo
git clone https://github.com/sophie-nguyenthuthuy/sample-poc-hybrid.git
cd sample-poc-hybrid

# Copy .env file (one-time)
make env
# Creates .env from .env.example with default values
```

### 2. Generate Kafka Cluster UUID

```bash
make kafka-id
# Output: abc123def456ghi789...
# Copy the UUID and paste into .env, key KAFKA_CLUSTER_ID
```

**Edit `.env`:**
```bash
# Find and replace this line:
KAFKA_CLUSTER_ID=<your-uuid-here>

# Example:
KAFKA_CLUSTER_ID=MkQwODI4NTc0NjAxNDM2Mzk0
```

### 3. Bring Up MVP Stack (Default Profile)

```bash
make up-hybrid
# Brings up: Spark (master + worker), Kafka, MinIO, Hive Metastore, Postgres, Trino

# Wait ~60–90 seconds for containers to fully initialize
# Check status:
make ps
```

**Expected output from `make ps`:**
```
CONTAINER ID  IMAGE                              STATUS
...           bitnami/spark:4.0.0                Up 30s (healthy)
...           apache/kafka:4.0.0                 Up 30s (healthy)
...           minio/minio:latest                 Up 30s (healthy)
...           postgres:17                        Up 30s (healthy)
...           trinodb/trino:470                  Up 30s (healthy)
```

### 4. Smoke Test (Verify Spark + Delta Works)

```bash
make smoke-hybrid
# Runs: spark-submit infra/spark/scripts/smoke-test.py
# Writes 1 row to Delta, reads it back, verifies count
# Output: "✓ Smoke test passed"
```

### 5. Seed OLTP Data (Devices + Locations)

```bash
make seed-oltp
# Runs: source/seed-oltp.py
# Creates Postgres tables: devices, locations, device_config
# Inserts: 100 devices, 20 Hanoi districts, 1 config per device
# Duration: ~5 seconds
```

### 6. Stream IoT Data (Background)

```bash
# Terminal 1: Start the simulator + streaming job
make seed-iot RATE=100 DUR=60 &
# Generates 100 IoT events/second for 60 seconds
# In parallel:
make stream-iot-bronze
# Consumes from Kafka, writes to bronze.iot_events
# Keep running; press Ctrl+C to stop
```

**Monitor stream status:**
```bash
# Terminal 2:
make stream-status
# Shows Kafka lag, Spark streaming progress
```

**Stop stream gracefully:**
```bash
make stop-stream-iot
# Sends SIGTERM to Spark driver; drains current batch, exits
```

### 7. Seed & Ingest Media

```bash
make seed-media COUNT=60
# Generates 60 images/videos in MinIO raw-media/
# Duration: ~10 seconds

make batch-media-bronze
# Scans MinIO, extracts EXIF/ffprobe, creates thumbnails
# Writes to bronze.media_objects
# Duration: ~30 seconds
```

### 8. Run Medallion Transforms

```bash
make build-silver
# Equivalent to:
#   make build-silver-iot
#   make build-silver-media
# Deduplicates + enriches bronze → silver
# Duration: ~1 minute

make build-gold
# Equivalent to:
#   make build-gold-iot-hourly
#   make build-gold-device-health
#   make build-gold-media-storage
#   make build-gold-correlation
# Aggregates silver → gold marts
# Duration: ~1 minute
```

### 9. Validate with Trino

```bash
make trino-validate
# Runs: bi/trino_validation_queries.sql
# Outputs: Row counts from bronze, silver, gold
# Sanity checks: dedup proof, outlier rates, mart snapshot counts
```

### 10. (Optional) Add Orchestration (Airflow)

```bash
make up-airflow
# Brings up: Airflow scheduler + webserver + dag-processor
# Wait ~30 seconds for Airflow to initialize

make airflow-ui
# Opens http://localhost:8080 (Airflow web UI)
# Login: admin / admin
# View 3 DAGs: streaming_iot_bronze_supervisor, hybrid_batch_pipeline, maintenance_daily
```

**Trigger Airflow DAG manually:**
```bash
make airflow-trigger DAG=hybrid_batch_pipeline
# Triggers DAG 2 (hourly batch), which runs immediately
```

### 11. (Optional) Add BI Dashboards (Superset)

```bash
make up-bi
# Brings up: Superset + Trino connector
# Wait ~30 seconds for Superset to initialize

make superset-ui
# Opens http://localhost:8088 (Superset web UI)
# Login: admin / admin

make superset-bootstrap
# Creates Trino connection + sample datasets + 3 dashboards
```

**Expected dashboards:**
- IoT Real-Time Gauge (device readings, last 1 hour).
- Device Health (last_seen, lag, anomaly_rate).
- Media Storage Usage (file count, bytes, top devices).

### 12. (Optional) Full Stack + UC OSS (Experimental)

```bash
make up-full
# Brings up MVP + Airflow + additional Spark worker

make up-uc
# Brings up UC OSS on separate profile (Spark-only; Trino won't read it)
# Use `make up-uc` AFTER `make up-hybrid` (or alone for UC experiments)
```

## Profiles Cheatsheet

| Profile | Services | Use Case | Command |
|---------|----------|----------|---------|
| **mvp** (default) | Spark, Kafka, MinIO, HMS, Postgres, Trino | Base lakehouse | `make up-hybrid` |
| **uc** | Adds Unity Catalog OSS | Spark-only experimentation | `make up-uc` |
| **hms** | Alias for mvp (emphasize HMS) | Clarify catalog choice | `docker compose --profile hms up` |
| **airflow** | Adds Airflow scheduler + webserver | Orchestration | `make up-airflow` |
| **bi** | Adds Superset | BI dashboards | `make up-bi` |
| **full** | mvp + airflow + extra Spark worker | Everything | `make up-full` |

**Combine profiles:**
```bash
# MVP + Airflow + Superset
docker compose --profile airflow --profile bi up -d --build

# MVP + UC + Airflow + Superset
docker compose --profile uc --profile airflow --profile bi up -d --build
```

## Port Mapping

| Service | Port | URL | Notes |
|---------|------|-----|-------|
| Spark Master UI | 8080 | http://localhost:8080 | Spark DAG visualization |
| Spark Worker UI | 8081 | http://localhost:8081 | Executor metrics |
| Airflow Web | 8080* | http://localhost:8080 | (conflicts with Spark; reassign if both running) |
| Superset | 8088 | http://localhost:8088 | Dashboard UI |
| Trino Coordinator | 8089 | http://localhost:8089 | Query UI (alternative to CLI) |
| MinIO Console | 9001 | http://localhost:9001 | S3 management (user: minioadmin / pw: minioadmin) |
| Kafka Broker | 9092 | localhost:9092 | Client connections |
| Postgres | 5432 | localhost:5432 | JDBC/SQL client |
| Hive Metastore | 9083 | localhost:9083 | Thrift (internal) |

**Note:** Ports differ by +5 from `sample-poc` to allow both POCs running simultaneously.

## Common Commands

```bash
# Check container health
make ps
make healthcheck

# View logs
make logs                          # tail all
docker compose logs -f spark-master  # single service

# Database access
make psql-meta                     # Connect to metastore DB
make psql-oltp                     # Connect to OLTP DB

# Kafka debugging
make kafka-topics                  # List topics
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic iot.sensors \
  --from-beginning \
  --max-messages 5

# Spark SQL CLI
docker compose exec spark-master /opt/bitnami/spark/bin/spark-sql \
  -c spark.sql.catalogImplementation=hive

# Trino CLI
make trino-cli                     # Interactive Trino shell
```

## Clean Up & Reset

### Pause / Stop (Keep Volumes)

```bash
make down-hybrid
# Stops containers but keeps PostgreSQL data, MinIO data, Delta checkpoints
# Restart with `make up-hybrid`
```

### Full Clean (DESTRUCTIVE)

```bash
make clean-hybrid
# Removes containers + ALL volumes
# Data is lost; next `make up-hybrid` starts fresh
```

### Partial Reset (Warehouse Only)

```bash
make reset-warehouse
# Drops bronze/silver/gold schemas from HMS
# Wipes bronze/, silver/, gold/, _checkpoints/ from MinIO
# Keeps raw-media/ and thumbnails/
# Useful after first run if you want to replay the demo
```

## Health Checks & Troubleshooting

**All services healthy?**
```bash
make healthcheck
# Checks: Spark, Kafka, MinIO, Postgres, HMS, Trino
```

**Spark issues?**
```bash
docker compose logs spark-master | tail -50
docker compose exec spark-master jps -l  # List Java processes
```

**Kafka issues?**
```bash
make kafka-topics
# Lists iot.sensors, iot.sensors.dlq
```

**MinIO issues?**
```bash
docker compose exec minio-bootstrap mc ls local/lakehouse/
# Lists buckets and prefixes
```

**Postgres issues?**
```bash
make psql-meta
# In psql:
SELECT schema_name FROM information_schema.schemata;
```

**Trino connectivity?**
```bash
make trino-cli
# In Trino:
SHOW CATALOGS;
SHOW SCHEMAS FROM hive;
SELECT * FROM hive.bronze.iot_events LIMIT 1;
```

See [`troubleshooting.md`](./troubleshooting.md) for more detailed recovery procedures.

## Validation Checklist — "POC is Healthy"

- [ ] `make ps` shows all containers status "Up" and "healthy".
- [ ] `make smoke-hybrid` returns "✓ Smoke test passed".
- [ ] `make seed-oltp` completes without errors; Postgres contains 100 devices.
- [ ] `make seed-iot RATE=100 DUR=60 &` generates 100+ events/sec; `make stream-iot-bronze` consumes without lag.
- [ ] `make seed-media COUNT=60` and `make batch-media-bronze` complete; MinIO has thumbnails/.
- [ ] `make build-silver` and `make build-gold` complete without errors.
- [ ] `make trino-validate` shows row counts matching expected (bronze ≥ 6000, gold ≥ 100).
- [ ] Superset dashboards display ≥ 1 chart per dashboard (after `make up-bi` + `make superset-bootstrap`).

If all pass, the POC is ready for demos or manual exploration.

## Production Considerations

**This is a POC, not production-ready.** Migration would require:

### Compute
- **Airflow Limitation:** Replace streaming_iot_bronze_supervisor DAG with **K8s Deployment** (rolling restarts) or **Databricks Job continuous** (native streaming).
- **Scale-out:** Replace Spark LocalExecutor with YARN/K8s cluster (multiple nodes).

### Catalog
- **Trino OSS Limitation:** Move to **Starburst** or **post-470 OSS** release for Unity Catalog support over Thrift.
- Alternatively, stick with HMS but add **Ranger** for row/column security.

### Storage
- **MinIO Limitations:** Switch to cloud object storage (**AWS S3**, **Azure Blob**, **GCS**).
- Enable multi-region replication and versioning.

### Orchestration
- **Airflow LocalExecutor Limitation:** Switch to **Kubernetes Executor** or **Databricks Workflows**.
- Add monitoring: Prometheus + Grafana, OpenTelemetry integration.

### Reliability
- **Single-node Kafka:** Expand to **Kafka cluster** with replication factor ≥ 3.
- Add **data quality monitoring** (Great Expectations, dbt tests).
- Implement **backup & recovery** procedures (automated snapshots, cross-region failover).

### Security
- **No authentication** (POC uses simple passwords). Add **OAuth2/OIDC** via Keycloak or cloud IdP.
- **No encryption at rest/in transit.** Enable TLS for all services, KMS for secrets.
- **No audit logging.** Implement centralized logging (ELK, Splunk).

### Operations
- **Monitoring & Alerting:** Add dashboards for job failures, data quality, storage usage.
- **Runbooks & Playbooks:** Document incident response, scaling procedures.
- **Cost optimization:** Monitor resource usage; schedule off-hours shutdowns if applicable.

---

**Deployment Guide Version:** 1.0 (Local POC only) | **Last Updated:** 2026-06-19

For detailed system architecture, see [`system-architecture.md`](./system-architecture.md). For troubleshooting, see [`troubleshooting.md`](./troubleshooting.md).
