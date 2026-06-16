---
phase: 5
title: Airflow Orchestration
status: completed
priority: P2
effort: 1d
dependencies:
  - 3
  - 4
---

# Phase 5: Airflow Orchestration

## Overview
Wire the manual scripts from Phases 3–4 into one scheduled Airflow DAG:
`extract_load_bronze → transform_silver → transform_gold`. This proves the pipeline is
**orchestrated and repeatable**, not a pile of hand-run scripts — the operational half of
the architecture's L3 orchestration layer.

## Requirements
- Functional: one DAG runs the full chain in order; a manual trigger after `seed-append`
  performs an incremental run touching only deltas.
- Non-functional: Airflow added to Compose stays within the laptop RAM budget
  (LocalExecutor, not Celery); DAG parse + run is reliable.

## Architecture
```
DAG: lakehouse_elt  (schedule: @hourly or manual)
  task extract_load_bronze  ──►  task transform_silver  ──►  task transform_gold
        (Phase 3 entrypoint)        (Phase 4)                  (Phase 4)
```
- Executor: **LocalExecutor** (lightest that still shows real scheduling).
- Tasks call the existing pipeline entrypoints (PythonOperator or a thin BashOperator on
  the same image) — reuse Phase 3/4 code, do NOT reimplement logic in the DAG.
- Pipeline code mounted/installed into the Airflow image so imports resolve.

## Related Code Files
- Create: `orchestration/dags/lakehouse_elt_dag.py`
- Create: `orchestration/Dockerfile` (Airflow + pipeline deps: polars, pyiceberg, connectorx)
- Modify: `docker-compose.yml` (airflow-scheduler, airflow-webserver, init container for
  `airflow db migrate` + admin user; metadata = `airflow` DB on shared `meta-db`)
- Modify: `.env.example` (Airflow `AIRFLOW__CORE__EXECUTOR=LocalExecutor`, fernet key)
- Create: `Makefile` targets `airflow-up`, `dag-trigger`

## Implementation Steps
1. Build `orchestration/Dockerfile` from official Airflow image; install pipeline package
   (Phase 3/4 code) so DAG tasks import `pipeline.*` directly.
2. Add Airflow services to Compose: init (db migrate + create admin), scheduler, webserver
   (port 8080). Use LocalExecutor. **Airflow metadata lives in an `airflow` database on the
   shared `meta-db` Postgres from Phase 1 — do NOT add a new Postgres container.** Reuse the
   shared bridge network so tasks reach `source-db`, `lakekeeper`, `minio`.
3. `lakehouse_elt_dag.py`: 3 tasks chained with `>>`, retries=1, sensible `start_date`,
   `catchup=False`. Parameterize `--full` vs incremental via DAG param/Variable.
4. Confirm tasks read the SAME watermark store as manual runs (no divergence between
   `make ingest-bronze` and the DAG path).
5. Trigger once for baseline (full), then `make seed-append` + trigger again (incremental);
   inspect task logs + Iceberg snapshots to confirm delta-only bronze write.
6. Verify failure handling: kill one task, confirm downstream doesn't run and a retry works.

## Success Criteria
- [ ] DAG visible + parseable in Airflow UI; manual trigger runs all 3 tasks green.
- [ ] Full run lands bronze→silver→gold; gold queryable in Trino afterward.
- [ ] Post-`seed-append` trigger does an incremental run (delta-only bronze, verified in logs).
- [ ] DAG reuses Phase 3/4 code (no duplicated transform logic in the DAG file).
- [ ] Stack still boots within RAM budget with Airflow running.

## Risk Assessment
- **Airflow RAM/boot weight** → LocalExecutor only; skip Celery/Redis/Flower; pin
  `AIRFLOW__CORE__LOAD_EXAMPLES=False`.
- **Pipeline deps missing in Airflow image** → bake them into `orchestration/Dockerfile`;
  pin versions matching Phase 3/4.
- **Watermark divergence between manual + DAG runs** → single shared watermark store path
  (env-configured), exercised by both; assert in step 4.
- **Webserver vs scheduler version skew** → build both from the same Dockerfile.
