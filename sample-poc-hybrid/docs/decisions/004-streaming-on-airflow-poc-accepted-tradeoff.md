# ADR-004 — Streaming Spark job supervised by Airflow (accepted POC tradeoff)

**Status:** Accepted as a POC tradeoff (will be revisited for production).
**Date:** 2026-06-19 (Validation Session 1, Q2).

## Context

The IoT bronze pipeline is **Spark Structured Streaming**, which is naturally long-running. Airflow DAGs are naturally short-lived tasks. Putting one inside the other is universally flagged as an anti-pattern: Airflow's scheduler is built around DAGs that complete, not DAGs that occupy a worker slot indefinitely.

Three options:

1. Keep the streaming DAG (`streaming_iot_bronze_supervisor`) with `retries=3` + exponential backoff — Airflow becomes the supervisor for the JVM process.
2. Move the streaming job to a sibling `docker-compose` service (`streaming-iot-bronze`) with `restart: unless-stopped`; Airflow only handles batch + maintenance.
3. Run the streaming job as Spark Connect short-lived micro-batches kicked off by Airflow on a schedule — gives up latency for orchestration purity.

## Decision

**Option 1 — keep the streaming DAG.** Documented as a known POC tradeoff.

## Rationale

- Single orchestration surface. Operators see "all the IoT work" in one place (Airflow UI), without juggling between Airflow + compose service logs + maybe a third K8s manifest.
- Matches the existing `sample-poc` story where Airflow is the single front door.
- The retry-on-exit semantics actually serve as a useful supervisor for the POC's reliability story — a crash bubbles to Airflow alerting; the operator can intervene from the UI.

## Consequences

- The `streaming_iot_bronze_supervisor` DAG is `schedule=None`; triggered once at boot, lives until it crashes or is paused.
- The maintenance DAG (`maintenance_daily`) explicitly pauses the streaming DAG, runs OPTIMIZE/VACUUM, then resumes (Validation Session 1, Q3).
- **Production must move to one of:**
  - **Spark on Kubernetes Deployment** (`apiVersion: apps/v1` with a single-replica spark-submit pod).
  - **Databricks Job continuous** (the cleanest equivalent of "Spark Streaming as a managed long-running task").
  - **An always-on Spark Connect client** that Airflow only nudges to restart.

## Reversibility

A future plan can extract the streaming supervisor into a compose service (option 2) in a few hours: move the spark-submit args from `spark_submit_defaults.py` into a `command:` block in `docker-compose.yml`, delete the DAG, document the restart policy. The medallion downstream isn't coupled to *how* the stream runs — only that bronze keeps receiving rows.
