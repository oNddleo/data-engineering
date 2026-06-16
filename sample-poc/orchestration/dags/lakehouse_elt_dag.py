"""Airflow DAG: orchestrate the lakehouse ELT chain.

extract_load_bronze -> transform_silver -> transform_gold

Tasks shell out to the Phase 3/4 pipeline scripts (baked into the image at
/opt/pipeline) so there is NO transform logic duplicated here. Service-DNS
hostnames (source-db, lakekeeper, minio) come from the container environment
set in docker-compose, so the DAG path and manual `make` runs share behavior
and the same watermark store.

Trigger incremental (default) or full via the `full_reload` DAG param.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator

PIPE = "cd /opt/pipeline &&"

with DAG(
    dag_id="lakehouse_elt",
    description="Postgres -> Iceberg bronze/silver/gold (Polars + PyIceberg)",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    # Serialize runs: the watermark store is a read-modify-write JSON object, so two
    # concurrent runs could lose an update. One active run at a time avoids the race.
    max_active_runs=1,
    default_args={"retries": 1},
    params={"full_reload": Param(False, type="boolean")},
    tags=["lakehouse", "poc"],
) as dag:
    extract_load_bronze = BashOperator(
        task_id="extract_load_bronze",
        bash_command=(
            PIPE + " python extract_load_bronze.py "
            "{{ '--full' if params.full_reload else '' }}"
        ),
    )
    transform_silver = BashOperator(
        task_id="transform_silver",
        bash_command=PIPE + " python transform_silver.py",
    )
    transform_gold = BashOperator(
        task_id="transform_gold",
        bash_command=PIPE + " python transform_gold.py",
    )

    extract_load_bronze >> transform_silver >> transform_gold
