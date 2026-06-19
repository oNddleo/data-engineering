# Design Guidelines — Hybrid Lakehouse POC

Backend POC only (no frontend UI). Guidelines cover BI dashboard authoring, file naming, and code style enforcement.

## Superset Dashboard Conventions

This is a backend POC; all BI work is in Superset against Trino queries on gold marts.

### Dashboard Creation Pattern

**1. Database Connection:**
- Use `Trino (Delta Lakehouse)` connection (configured at bootstrap).
- Schema: `default` (HMS warehouse default).

**2. Dataset Naming Convention:**
```
gold_<domain>_<granularity>

Examples:
  gold_iot_hourly_metrics      (IoT metrics, 1-hour grain)
  gold_iot_device_health       (Device snapshot, daily)
  gold_media_storage_daily     (Media aggregates, daily)
  gold_iot_media_correlation   (Cross-domain, daily)
```

**3. Chart Naming Convention:**
```
<Dashboard>_<MetricType>_<Dimension>

Examples:
  IoT_RealTime_AvgValueByDevice
  IoT_RealTime_AnomalyCounts
  DeviceHealth_Status_ByLocation
  MediaStorage_TopDevices_BySize
```

**4. One Chart per Gold Mart Pattern:**
- Each chart queries a single gold table (joins allowed, but single mart as primary source).
- Avoid duplicating logic; if multiple charts need same query, save as dataset instead.

**5. Refresh Rate:**
- Gold tables refresh hourly (or daily for snapshots).
- Set Superset cache timeout to 300 seconds (5 min) to balance freshness vs. query load.

### Sample Dashboard Schemas

**Dashboard 1: IoT Real-Time Gauge**
```
Tables: gold.iot_hourly_metrics (last 1 hour)
Charts:
  - gauge: avg_value (last hour, all devices)
  - time_series: avg_value over time (line, stacked by device)
  - table: top 10 devices by p95_value (sortable)
```

**Dashboard 2: Device Health Status**
```
Tables: gold.device_health (latest snapshot)
Charts:
  - gauge: healthy device count / total (%)
  - table: all devices (device_id, last_event_ts, lag_minutes, health_status, anomaly_rate_24h)
  - bar: health_status distribution (healthy / lagging / anomalous)
```

**Dashboard 3: Media Storage Usage**
```
Tables: gold.media_storage_daily (latest day)
Charts:
  - gauge: total bytes used (in TB)
  - time_series: bytes over time (line, cumulative)
  - table: top 5 devices by file count (device_id, file_count, bytes, avg_file_size)
```

### SQL Lab Workflow

Use SQL Lab for ad-hoc queries during development/troubleshooting:

```sql
-- Example: Query gold.iot_hourly_metrics
SELECT
  device_id,
  metric_hour,
  avg_value,
  p95_value,
  anomaly_count,
  event_count
FROM hive.gold.iot_hourly_metrics
WHERE metric_date >= current_date - 7
ORDER BY metric_hour DESC
LIMIT 100
```

**Tips:**
- Use fully qualified names: `hive.<schema>.<table>` for Trino compatibility.
- Cache queries that are reused across dashboards.
- Test WHERE clause selectivity; Trino scans partitions only if predicate includes partition key.

## File Naming & Project Policy

**Principle:** Self-documenting names for LLM tools (grep, codegraph, file search).

### Python Modules (Importable)
- **Case:** snake_case
- **Length:** Descriptive, no abbreviations
- **Examples:**
  ```
  spark_session.py              ✓ (factory for Spark sessions)
  media_extractors.py           ✓ (EXIF, ffprobe extraction)
  unit_normalizer.py            ✓ (sensor unit conversions)
  dlq_writer.py                 ✓ (dead-letter queue logic)
  dim_loader.py                 ✓ (dimension broadcast join)
  ```

### Entry Scripts (spark-submit)
- **Case:** kebab-case (signals "not meant for import")
- **Length:** Descriptive
- **Examples:**
  ```
  streaming-iot-bronze.py        ✓ (Kafka → bronze stream)
  batch-media-bronze.py          ✓ (MinIO → bronze batch)
  build-silver-iot.py            ✓ (bronze → silver transform)
  build-gold-iot-hourly.py       ✓ (silver → gold hourly agg)
  maintenance-optimize.py        ✓ (OPTIMIZE + VACUUM)
  ```

### Airflow DAGs
- **Case:** snake_case (Airflow autodiscovery requires this)
- **Examples:**
  ```
  streaming_iot_bronze_supervisor.py   ✓ (long-running stream)
  hybrid_batch_pipeline.py              ✓ (hourly batch DAG)
  maintenance_daily.py                  ✓ (daily maintenance DAG)
  ```

### Configuration Files
- **Case:** kebab-case or snake_case (JSON-compatible, any valid filename)
- **Location:** `pipeline/conf/` (flat, not nested)
- **Format:** JSON-compatible YAML (no PyYAML syntax)
- **Examples:**
  ```
  streaming-iot-bronze.yaml     ✓ (matches entry script name)
  batch-media-bronze.yaml       ✓
  build-silver-iot.yaml         ✓
  build-gold-iot-hourly.yaml    ✓
  maintenance-optimize.yaml     ✓
  ```

### Documentation Files
- **Case:** kebab-case or descriptive words
- **Location:** `docs/` (flat or `docs/decisions/` for ADRs)
- **Examples:**
  ```
  project-overview-pdr.md       ✓ (product requirement doc)
  codebase-summary.md           ✓ (module guide)
  code-standards.md             ✓ (coding rules)
  system-architecture.md        ✓ (design overview)
  deployment-guide.md           ✓ (setup instructions)
  poc-architecture.md           ✓ (POC-specific diagram)
  demo-runbook.md               ✓ (step-by-step demo)
  7-layer-mapping.md            ✓ (reference alignment)
  troubleshooting.md            ✓ (error recovery)
  ```

### ADRs (Architecture Decision Records)
- **Pattern:** `NNN-kebab-case-title.md`
- **Examples:**
  ```
  docs/decisions/001-delta-vs-iceberg.md
  docs/decisions/002-oss-spark-vs-databricks.md
  docs/decisions/003-no-ml-inference-in-poc.md
  docs/decisions/004-streaming-on-airflow-poc-accepted-tradeoff.md
  ```

### Test Files
- **Case:** snake_case (Python convention)
- **Pattern:** `test_<module_or_feature>.py`
- **Examples:**
  ```
  tests/unit/test_unit_normalizer.py          ✓ (tests lib/unit_normalizer.py)
  tests/unit/test_media_extractors.py         ✓
  tests/unit/test_spark_pipeline_units.py     ✓ (generic pipeline logic)
  tests/integration/test_smoke_streaming.py   ✓ (end-to-end smoke test)
  ```

### Infrastructure Files
- **Case:** Mixed (follow service convention)
- **Examples:**
  ```
  infra/spark/Dockerfile                      ✓ (convention)
  infra/spark/spark-defaults.conf             ✓ (Spark config)
  infra/spark/log4j2.properties               ✓ (Log4j config)
  infra/kafka/create-topics.sh                ✓ (bash script)
  infra/postgres/init-meta.sql                ✓ (SQL)
  infra/hive-metastore/metastore-site.xml    ✓ (Hadoop config)
  ```

## Code Style Enforcement

**Linting:**
```bash
make lint-source       # Ruff format + check on source/
make lint-pipeline     # Ruff format + check on pipeline/
make lint-dags        # Ruff format + check on orchestration/dags/
```

**Type Checking:**
```bash
mypy --strict pipeline/spark_jobs/lib/
```

**Test Coverage:**
```bash
pytest --cov=pipeline tests/unit/
```

## Internationalization (i18n)

**Project Language:** English for code, comments, git commits, and most documentation.

**Exception:** Vietnamese is acceptable in:
- User-facing documentation (e.g., README intro, demo examples).
- Inline comments for Vietnamese team members (where context requires).
- Phase documentation (phase-*.md) may include Vietnamese explanations of design decisions.

**Rule:** Do NOT mix Vietnamese and English in the same code block. Use separate sections or clear language markers.

## No Emojis in Code

- ✓ Correct: `# TODO: Add EXIF extraction for JPG files`
- ✗ Incorrect: `# TODO: Add EXIF extraction for JPG files 📸`

Emojis are fine in:
- External communication (Slack, GitHub issues).
- Demo slides or presentations.

NOT in:
- Code comments or docstrings.
- Git commit messages.
- File names.
- Documentation files (unless explicitly approved).

## Architectural Patterns

### Pure-Function Libraries (`lib/` modules)

**Pattern:**
```python
# pipeline/spark_jobs/lib/media_extractors.py
from pyspark.sql import SparkSession, Column

def extract_exif(spark: SparkSession, binary_col: Column) -> Column:
  """Extract EXIF metadata from image binary."""
  # No side effects; returns a Column
  # Safe to call in distributed transforms
  pass
```

**Why:**
- Testable without Spark context.
- Reusable across multiple jobs.
- No hidden state or file I/O.

### Entry Scripts (spark-submit)

**Pattern:**
```python
# pipeline/spark_jobs/streaming-iot-bronze.py
import logging
from pipeline.spark_jobs.lib import spark_session, config_loader

logger = logging.getLogger(__name__)

if __name__ == "__main__":
  config = config_loader.load_config("pipeline/conf/streaming-iot-bronze.yaml")
  spark = spark_session.build_streaming_session("iot_events_streaming")
  # Job logic here
```

**Why:**
- Main block prevents accidental imports.
- Config loaded at startup (fail-fast if missing).
- Session built once and reused.

### Airflow DAGs (task SDK)

**Pattern:**
```python
# orchestration/dags/hybrid_batch_pipeline.py
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime

with DAG(
  "hybrid_batch_pipeline",
  schedule_interval="@hourly",
  start_date=datetime(2026, 6, 19),
  catchup=False,
) as dag:
  batch_media = SparkSubmitOperator(
    task_id="batch_media_bronze",
    application="pipeline/spark_jobs/batch-media-bronze.py",
  )
  # More tasks...
```

**Why:**
- Declarative (Airflow 3.0 task SDK).
- Repeatable scheduling.
- Task dependencies explicit.

## Documentation Standards

**README.md (Project Root):**
- Keep < 300 lines.
- Quick start, test, docs index.
- Link to full guides in `docs/`.

**Standalone Docs (in `docs/`):**
- Keep each < 250 lines (or split into modular files).
- Always link to related docs (cross-references).
- Include table of contents if > 150 lines.

**Inline Code Comments:**
- Explain *why*, not *what*.
- Use sparingly; code should be self-documenting.
- Avoid commented-out code (use git history instead).

---

**Guidelines Version:** 1.0 | **Last Updated:** 2026-06-19

See [`code-standards.md`](./code-standards.md) for detailed coding rules and [`deployment-guide.md`](./deployment-guide.md) for Superset setup instructions.
