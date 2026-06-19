# Code Standards — Hybrid Lakehouse POC

Guidelines for writing, organizing, and reviewing code in this Spark 4.0 + Delta Lake project. See [`codebase-summary.md`](./codebase-summary.md) for module layout and entry-point map.

## File Naming Convention

**Importable Modules:** `snake_case` (in `pipeline/spark_jobs/lib/`, `orchestration/dags/lib/`)
```
spark_session.py          ✓ Correct (importable)
media_extractors.py       ✓ Correct (importable)
```

**Entry-Point Scripts:** `kebab-case` (in `pipeline/spark_jobs/`, `orchestration/dags/`)
```
streaming-iot-bronze.py        ✓ Correct (spark-submit entry, not meant for import)
batch-media-bronze.py          ✓ Correct (spark-submit entry, not meant for import)
hybrid_batch_pipeline.py       ✓ EXCEPTION: Airflow autodiscovery requires snake_case
```

**Why this split?**
- `kebab-case` signals "entry script, not importable" to LLM tools (Grep, codegraph).
- `snake_case` signals "safe to import" and aligns with Python convention.
- **Exception:** Airflow DAGs MUST be `snake_case` because `airflow.models.DAG` uses `importlib` to auto-discover `.py` files. Kebab-case breaks the loader.

## Configuration Files

**Format:** JSON-compatible YAML (no PyYAML-specific syntax).

```yaml
{
  "bootstrap_servers": "kafka:9092",
  "source_topic": "iot.sensors",
  "delta_path": "s3a://lakehouse/bronze/iot_events",
  "checkpoint_path": "s3a://lakehouse/_checkpoints/bronze_iot_events",
  "max_offsets_per_trigger": 10000,
  "trigger_interval": "10 seconds",
  "create_table_if_missing": true
}
```

**Why JSON-compatible?**
- Eliminates `PyYAML` runtime dependency in Spark containers (reduces image size, attack surface).
- Works with pure Python `json` library.
- Can be parsed by Bash `jq` or `yq` on-the-fly.
- Human-readable (formatted as YAML).

**Usage in Spark:**
```python
import json

with open("pipeline/conf/streaming-iot-bronze.yaml", "r") as f:
    config = json.load(f)
```

## Idempotency Mechanics

**Core Principle:** All spark_jobs are idempotent (restarting produces the same result).

### Bronze Layer

**IoT Streaming:**
- Spark Structured Streaming writes inside `foreachBatch` with `txnAppId` + `txnVersion`.
- `txnAppId = "iot_events_streaming"`, `txnVersion = batch_id` (timestamp).
- Delta's built-in idempotency deduplicates retries automatically.
- **Code pattern:**
  ```python
  df.writeStream \
    .option("txnAppId", "iot_events_streaming") \
    .option("txnVersion", batch_id) \
    .mode("append") \
    .option("checkpointLocation", checkpoint_path) \
    .start()
  ```

**Media Batch:**
- Anti-join on `(object_key, etag)`.
- `etag = date_format(file_modtime) + '-' + file_length` (mimics S3 ETag logic).
- Same-second rewrites get different etag → new rows inserted.
- **Code pattern:**
  ```python
  existing_df = spark.table("bronze.media_objects") \
    .select("object_key", "etag")
  new_df = scan_s3(...) \
    .join(existing_df, on=["object_key", "etag"], how="anti")
  new_df.write.mode("append").saveAsTable("bronze.media_objects")
  ```

### Silver Layer

**Deduplication & Enrichment:**
- Use `row_number(1)` over `(partition_key)` ordered by `ingestion_ts DESC` to pick latest.
- Broadcast dimension tables (`dim_loader.py`).
- **Code pattern:**
  ```python
  from pipeline.spark_jobs.lib.dim_loader import load_dim_broadcast

  dedup_df = spark.table("bronze.iot_readings") \
    .select(
      row_number().over(Window.partitionBy("event_id").orderBy(desc("ingestion_ts"))).alias("rn"),
      "*"
    ) \
    .filter("rn == 1") \
    .drop("rn")

  dim_broadcast = load_dim_broadcast(spark, "devices")
  enriched_df = dedup_df.join(dim_broadcast, on="device_id", how="left")
  ```

**MERGE into Silver:**
- Always use `whenMatchedUpdateAll(condition="s.ingestion_ts > t.ingestion_ts")`.
- Ensures only newer rows overwrite.
- **Code pattern:**
  ```python
  target_df = spark.table("silver.iot_readings")
  source_df = spark.table("bronze.iot_readings") \
    .filter(condition) # additional business filters
  
  source_df.alias("s").join(
    target_df.alias("t"),
    on="event_id",
    how="full_outer"
  ).merge(
    condition="s.event_id = t.event_id"
  ).whenMatchedUpdateAll(
    condition="s.ingestion_ts > t.ingestion_ts"
  ).whenNotMatched().insertAll().execute()
  ```

### Gold Layer

**MERGE for Aggregates:**
- Use `MERGE INTO` for metric tables (IoT hourly, device health snapshots, media storage daily).
- Partition key is the rollup (e.g., `device_id + sensor_id + hour`).
- **Code pattern:**
  ```python
  metrics_df = spark.table("silver.iot_readings") \
    .groupBy(window("event_ts", "1 hour"), "device_id", "sensor_id") \
    .agg(avg("value").alias("avg_value"), percentile_approx("value", 0.95).alias("p95"))

  metrics_df.merge(
    condition="m.device_id = t.device_id AND m.sensor_id = t.sensor_id AND m.hour = t.hour"
  ).whenMatchedUpdateAll().whenNotMatched().insertAll().execute()
  ```

**OVERWRITE for Snapshots:**
- Use `OVERWRITE` for tables that are tiny or always fully recomputed (device health, media storage daily).
- Simpler than MERGE; no risk of stale rows from partial reruns.
- **Code pattern:**
  ```python
  health_df = spark.table("silver.iot_readings") \
    .groupBy("device_id") \
    .agg(max("event_ts").alias("last_seen"), ...)
  
  health_df.write.mode("overwrite").saveAsTable("gold.device_health")
  ```

## Pure-Function Libraries

All modules in `pipeline/spark_jobs/lib/` are **pure** (no side effects):

1. **No global state** — use SparkSession passed as argument.
2. **No file I/O** — return DataFrames, don't write.
3. **Type hints** — annotate all function signatures.
4. **Docstrings** — describe what, not how.

**Example:**
```python
def extract_exif(spark: SparkSession, binary_col: Column) -> Column:
  """Extract EXIF metadata from image binary.
  
  Args:
    spark: SparkSession
    binary_col: Column containing binary image data
    
  Returns:
    Column with EXIF dict (or null if not found)
  """
  # implementation
```

## Error Handling

**Spark Jobs:**
- Use try-catch at top level; log and fail fast.
- Write errors to DLQ (separate Delta table) for inspection.
- **Code pattern:**
  ```python
  try:
    df = spark.readStream.format("kafka").load()
    processed = transform(df)
    processed.writeStream.option("checkpointLocation", ...).start()
  except Exception as e:
    logger.error(f"Stream failed: {e}", exc_info=True)
    raise
  ```

**Config Loading:**
- Validate on startup; fail if config missing or invalid.
- **Code pattern:**
  ```python
  def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
      raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
      config = json.load(f)
    # Validate required keys
    required = ["bootstrap_servers", "source_topic", "delta_path"]
    if not all(k in config for k in required):
      raise ValueError(f"Config missing keys: {set(required) - set(config.keys())}")
    return config
  ```

## Testing

**Unit Tests** (in `tests/unit/`):
- Pure functions only (no Spark, no I/O).
- Parametrized for multiple input cases.
- **Code pattern:**
  ```python
  @pytest.mark.parametrize("sensor,value,expected", [
    ("temp_c", 25.0, 77.0),  # Celsius → Fahrenheit
    ("temp_f", 77.0, 77.0),  # Already F
  ])
  def test_unit_normalizer(sensor, value, expected):
    from pipeline.spark_jobs.lib.unit_normalizer import normalize
    assert normalize(sensor, value) == pytest.approx(expected)
  ```

**Integration Tests** (in `tests/integration/`, marked `slow`):
- Use testcontainers for ephemeral Kafka + MinIO.
- Marked with `@pytest.mark.slow` (opt-in via `pytest -m slow`).
- **Code pattern:**
  ```python
  @pytest.mark.slow
  def test_smoke_streaming(spark_session):
    # Use testcontainers
    # Write 10 records to Kafka
    # Run Spark.AvailableNow → Delta
    # Assert count == 10
  ```

## Code Review Action Items

All code-review items from Phase 1–9 reports have been applied and verified:

### Phase 1 (Infrastructure)

| Item | Category | Applied? | Commit Ref |
|------|----------|----------|-----------|
| C1: HMS primary (not UC OSS) | Critical | ✓ | 3763b81 |
| C2: UC path to `/home/unitycatalog/` | Critical | ✓ | 3763b81 |
| C3: UC healthcheck via `/dev/tcp/` | High | ✓ | 3763b81 |
| C4: Remove Spark `command:` override | High | ✓ | 3763b81 |
| H2: Kafka auto-format from CLUSTER_ID | High | ✓ | 3763b81 |
| H4: `depends_on` with `service_completed_successfully` | High | ✓ | 3763b81 |
| M1: Spark-worker healthcheck (curl /:8081) | Medium | ✓ | 3763b81 |
| M4: Trino healthcheck (use `/usr/lib/trino/bin/health-check`) | Medium | ✓ | 3763b81 |

### Phases 2–9

All subsequent phases inherited the cleaned Phase 1 base. No blocking items carried forward.

## Style Guidelines

**Python:**
- Format with `ruff format` (default config).
- Type-check with `mypy --strict` (strict mode on all `.py` files).
- No f-strings on untrusted input (use parameterized logging).
- Max line length: 100 chars (ruff default).

**SQL:**
- Use lowercase keywords (`select`, `from`, `where`).
- Indent sub-queries 2 spaces.
- Use meaningful table aliases (`s` for source, `t` for target in MERGE).

**Configuration:**
- Sort keys alphabetically within each section.
- Include comments above non-obvious fields (but format remains JSON-compatible).

**Git Commits:**
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- No AI references in messages.
- Keep focused on actual code changes.

## Documentation in Code

**Docstrings (PEP 257):**
```python
def build_streaming_session(
    app_name: str,
    *,
    stop_gracefully_on_shutdown: bool = True,
) -> SparkSession:
  """Return a SparkSession with Bronze-stream-friendly defaults applied.

  `spark.streaming.stopGracefullyOnShutdown=true` lets SIGTERM drain the
  current micro-batch before exiting.

  Args:
    app_name: Name for the Spark application.
    stop_gracefully_on_shutdown: Enable graceful stop on shutdown. Default True.

  Returns:
    SparkSession configured for streaming workloads.
  """
```

**Inline Comments:**
- Explain *why*, not *what*.
- Use for non-obvious business logic or performance tricks.

```python
# WHY: DLQ topic is separate to avoid creating a recursive loop if DLQ itself fails to parse.
dlq_df.write.mode("append").option("path", dlq_path).saveAsTable("bronze.iot_events.dlq")
```

## Performance Considerations

1. **Broadcast Dimensions:** Always broadcast dim tables in joins (< 100 MB).
   ```python
   dim_bc = spark.broadcast(dim_df)
   df.join(dim_bc, ..., how="left")
   ```

2. **Partitioning:** Partition large tables by `ingestion_date` or `metric_date` to prune scans.
   ```python
   df.write.partitionBy("ingestion_date").mode("append").saveAsTable(...)
   ```

3. **ZORDER:** Use Delta's ZORDER for frequently filtered columns (not partitioned).
   ```sql
   OPTIMIZE table_name ZORDER BY device_id, sensor_id
   ```

4. **Checkpointing:** Streaming jobs require checkpoint location for restarts.
   ```python
   checkpoint_path = "s3a://lakehouse/_checkpoints/bronze_iot_events"
   df.writeStream.option("checkpointLocation", checkpoint_path).start()
   ```

## Logging

**Use Python logging, not print():**
```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Processing {count} records from {topic}")
logger.error(f"Failed to write batch: {error}", exc_info=True)
```

**Spark Logs:**
- Configured via `infra/spark/log4j2.properties`.
- Set to INFO level in production (DEBUG in dev).

---

**Standards Version:** 1.0 | **Last Updated:** 2026-06-19

For questions, see [`codebase-summary.md`](./codebase-summary.md) (module map), [`plan.md`](../plan.md) (phases), or [`poc-architecture.md`](./poc-architecture.md) (overview).
