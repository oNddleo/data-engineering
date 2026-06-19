"""DAG 1 — keep the IoT bronze stream alive.

Pattern: a single `@task` blocks on `docker exec spark-master spark-submit
streaming-iot-bronze.py`. When the stream exits (driver crash, OOM, manual
stop), the task fails. Airflow retries up to 3x with exponential backoff,
restarting the stream from its checkpoint.

`schedule=None` — operator triggers manually after stack boot; subsequent
runs are driven by the retry policy, not the scheduler.

This is the validation-accepted POC tradeoff (Q2 Session 1): true
production usage would put the streaming job under K8s Deployment or
Databricks Job continuous, not an Airflow DAG.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta

from airflow.sdk import dag, task

from lib.spark_submit_defaults import spark_submit_in_master


@dag(
    dag_id="streaming_iot_bronze_supervisor",
    description="Long-running supervisor for the IoT bronze Structured Streaming job.",
    schedule=None,
    start_date=datetime(2026, 6, 19),
    catchup=False,
    max_active_runs=1,
    tags=["poc-hybrid", "streaming", "bronze"],
    default_args={
        "owner": "data-eng",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "execution_timeout": None,
    },
)
def streaming_iot_bronze_supervisor():
    @task
    def supervise_stream() -> None:
        cmd = spark_submit_in_master(
            script="streaming-iot-bronze.py",
            config="streaming-iot-bronze.yaml",
            app_name="iot-bronze-stream",
        )
        # check=True raises CalledProcessError on non-zero exit, which
        # Airflow surfaces as task failure and triggers the retry policy.
        subprocess.run(cmd, check=True)

    supervise_stream()


streaming_iot_bronze_supervisor()
