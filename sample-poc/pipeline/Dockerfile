# Lightweight runner for the Phase 3/4 pipeline scripts, executed INSIDE the
# lakehouse network. Running in-network is what lets the scripts reach the stack
# by service DNS (minio:9000, lakekeeper:8181, source-db:5432) — the exact same
# endpoints Lakekeeper vends and that Airflow uses, so host vs container parity
# is no longer a problem.
FROM python:3.12-slim

WORKDIR /app

# Same pinned deps as Airflow's pipeline layer (polars, pyiceberg, connectorx, ...).
COPY pipeline/requirements.txt /tmp/pipeline-requirements.txt
RUN pip install --no-cache-dir -r /tmp/pipeline-requirements.txt

# Pipeline source (scripts run with /app as CWD, matching the old `cd pipeline`).
COPY pipeline /app
