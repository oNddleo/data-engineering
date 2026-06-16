# Airflow image with the pipeline code + its deps baked in, so DAG tasks can
# run the Phase 3/4 scripts directly (no logic duplicated in the DAG).
ARG AIRFLOW_VERSION=2.10.3
FROM apache/airflow:${AIRFLOW_VERSION}

# pipeline deps (polars, pyiceberg, connectorx, ...) — same versions as host runs
COPY pipeline/requirements.txt /tmp/pipeline-requirements.txt
RUN pip install --no-cache-dir -r /tmp/pipeline-requirements.txt

# pipeline source available on PYTHONPATH at /opt/pipeline
COPY pipeline /opt/pipeline
ENV PYTHONPATH=/opt/pipeline
