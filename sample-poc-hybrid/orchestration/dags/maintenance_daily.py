"""DAG 3 — daily Delta maintenance: pause stream → OPTIMIZE/VACUUM → resume.

Validation Session 1 Q3 ruled out the "trust Delta Serializable" approach
in favour of a sequential bookend that guarantees no concurrent writer
during OPTIMIZE. The maintenance window is 02:00 local.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta

import urllib.request

from airflow.sdk import dag, task

from lib.spark_submit_defaults import spark_submit_in_master

STREAM_DAG_ID = "streaming_iot_bronze_supervisor"
SPARK_MASTER_JSON = "http://spark-master:8080/json/"
WAIT_TIMEOUT_SECONDS = 600
POLL_INTERVAL_SECONDS = 5


@dag(
    dag_id="maintenance_daily",
    description="Daily OPTIMIZE + VACUUM bookended by stream pause/resume.",
    schedule="0 2 * * *",
    start_date=datetime(2026, 6, 19),
    catchup=False,
    max_active_runs=1,
    tags=["poc-hybrid", "maintenance", "delta"],
    default_args={
        "owner": "data-eng",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(hours=1),
    },
)
def maintenance_daily():
    @task
    def pause_streaming() -> None:
        subprocess.run(["airflow", "dags", "pause", STREAM_DAG_ID], check=True)

    @task
    def wait_streaming_stopped() -> None:
        """Poll the Spark master REST API until no live app holds a driver."""
        deadline = time.time() + WAIT_TIMEOUT_SECONDS
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(SPARK_MASTER_JSON, timeout=5) as resp:
                    import json
                    payload = json.loads(resp.read())
                active = [a for a in payload.get("activeapps", []) if a.get("state") == "RUNNING"]
                if not active:
                    return
            except Exception as e:  # noqa: BLE001
                print(f"spark master probe failed (retrying): {e}")
            time.sleep(POLL_INTERVAL_SECONDS)
        raise RuntimeError(f"streaming app still active after {WAIT_TIMEOUT_SECONDS}s")

    @task
    def run_maintenance() -> None:
        cmd = spark_submit_in_master(
            script="maintenance-optimize.py",
            config="maintenance-optimize.yaml",
            app_name="delta-maintenance",
        )
        subprocess.run(cmd, check=True)

    @task(trigger_rule="all_done")
    def resume_streaming() -> None:
        """Run regardless of maintenance success so we don't strand the stream."""
        subprocess.run(["airflow", "dags", "unpause", STREAM_DAG_ID], check=True)
        subprocess.run(["airflow", "dags", "trigger", STREAM_DAG_ID], check=True)

    pause = pause_streaming()
    wait = wait_streaming_stopped()
    maint = run_maintenance()
    resume = resume_streaming()

    pause >> wait >> maint >> resume


maintenance_daily()
