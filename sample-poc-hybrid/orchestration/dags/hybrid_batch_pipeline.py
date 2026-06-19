"""DAG 2 — hourly batch: media bronze → silver iot/media → 4 gold marts.

Linear dependency chain. `max_active_runs=1` makes sure a slow run can't
overlap the next hourly trigger and step on its own MERGE.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta

from airflow.sdk import dag, task

from lib.spark_submit_defaults import spark_submit_in_master


def _spark_job(script: str, config: str, app_name: str) -> None:
    cmd = spark_submit_in_master(script=script, config=config, app_name=app_name)
    subprocess.run(cmd, check=True)


@dag(
    dag_id="hybrid_batch_pipeline",
    description="Hourly bronze→silver→gold pipeline for IoT + media.",
    schedule="@hourly",
    start_date=datetime(2026, 6, 19),
    catchup=False,
    max_active_runs=1,
    sla_miss_callback=None,
    tags=["poc-hybrid", "batch", "medallion"],
    default_args={
        "owner": "data-eng",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "execution_timeout": timedelta(minutes=30),
    },
)
def hybrid_batch_pipeline():
    @task
    def batch_media_bronze() -> None:
        _spark_job("batch-media-bronze.py", "batch-media-bronze.yaml", "media-bronze-batch")

    @task
    def build_silver_iot() -> None:
        _spark_job("build-silver-iot.py", "build-silver-iot.yaml", "silver-iot-build")

    @task
    def build_silver_media() -> None:
        _spark_job("build-silver-media.py", "build-silver-media.yaml", "silver-media-build")

    @task
    def build_gold_iot_hourly() -> None:
        _spark_job("build-gold-iot-hourly.py", "build-gold-iot-hourly.yaml", "gold-iot-hourly")

    @task
    def build_gold_device_health() -> None:
        _spark_job("build-gold-device-health.py", "build-gold-device-health.yaml", "gold-device-health")

    @task
    def build_gold_media_storage() -> None:
        _spark_job("build-gold-media-storage.py", "build-gold-media-storage.yaml", "gold-media-storage")

    @task
    def build_gold_correlation() -> None:
        _spark_job(
            "build-gold-iot-media-correlation.py",
            "build-gold-iot-media-correlation.yaml",
            "gold-iot-media-correlation",
        )

    media_bronze = batch_media_bronze()
    silver_iot = build_silver_iot()
    silver_media = build_silver_media()
    gold_hourly = build_gold_iot_hourly()
    gold_health = build_gold_device_health()
    gold_storage = build_gold_media_storage()
    gold_corr = build_gold_correlation()

    # Bronze fans into both silver branches; gold consumers depend on the
    # silver layer they read from.
    media_bronze >> silver_media
    silver_iot >> [gold_hourly, gold_health, gold_corr]
    silver_media >> [gold_storage, gold_corr]


hybrid_batch_pipeline()
