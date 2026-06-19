"""Spark-using unit tests — combined into one file so JVM starts once.

Covers three correctness invariants:
    - PERMISSIVE JSON parse with the IoT schema (Phase 3)
    - tag_outliers tags ≈3σ values per (device, sensor, day)  (Phase 5)
    - Delta MERGE on event_id is idempotent across reruns      (Phase 5)
"""

from __future__ import annotations

import importlib
import os

import pytest

from pyspark.sql import functions as F

from lib.iot_schema import IOT_EVENT_SCHEMA


# Import the streaming module via importlib because the file uses a hyphen.
spec = importlib.util.spec_from_file_location(
    "streaming_iot_bronze_mod",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "pipeline", "spark_jobs", "streaming-iot-bronze.py",
    ),
)
streaming_mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(streaming_mod)  # type: ignore[union-attr]

silver_spec = importlib.util.spec_from_file_location(
    "build_silver_iot_mod",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "pipeline", "spark_jobs", "build-silver-iot.py",
    ),
)
silver_mod = importlib.util.module_from_spec(silver_spec)  # type: ignore[arg-type]
silver_spec.loader.exec_module(silver_mod)  # type: ignore[union-attr]


# ---------- PERMISSIVE schema parse ----------

def test_iot_schema_marks_corrupt_json_with_null_event_id(spark):
    rows = [
        ('{"event_id":"e1","device_id":"dev-0001","sensor_type":"temperature",'
         '"value":24.0,"unit":"C","ts":"2026-06-19T05:11:11Z"}',),
        ('{not even json',),
        ('{"event_id":null,"device_id":"dev-0001","sensor_type":"humidity",'
         '"value":50.0,"unit":"%","ts":"2026-06-19T05:11:12Z"}',),
    ]
    raw = spark.createDataFrame(rows, ["value"])
    parsed = raw.select(
        F.col("value").alias("_raw_value"),
        F.from_json(F.col("value"), IOT_EVENT_SCHEMA).alias("payload"),
    )
    valid_count = parsed.where(F.col("payload.event_id").isNotNull()).count()
    invalid_count = parsed.where(F.col("payload.event_id").isNull()).count()
    assert valid_count == 1
    assert invalid_count == 2


# ---------- Outlier detection ----------

def test_tag_outliers_flags_values_outside_three_sigma(spark):
    base_ts = "2026-06-19T05:11:11Z"
    # 9 normal readings around 25, 1 extreme outlier at 200.
    rows = [
        ("e1", "dev-0001", "temperature", 25.0,  "C", base_ts),
        ("e2", "dev-0001", "temperature", 25.5,  "C", base_ts),
        ("e3", "dev-0001", "temperature", 24.8,  "C", base_ts),
        ("e4", "dev-0001", "temperature", 25.2,  "C", base_ts),
        ("e5", "dev-0001", "temperature", 24.9,  "C", base_ts),
        ("e6", "dev-0001", "temperature", 25.1,  "C", base_ts),
        ("e7", "dev-0001", "temperature", 25.3,  "C", base_ts),
        ("e8", "dev-0001", "temperature", 24.7,  "C", base_ts),
        ("e9", "dev-0001", "temperature", 25.4,  "C", base_ts),
        ("e10","dev-0001", "temperature", 200.0, "C", base_ts),
    ]
    df = spark.createDataFrame(rows, ["event_id", "device_id", "sensor_type", "value", "unit", "ts"])
    df = df.withColumn("event_ts", F.to_timestamp("ts")).withColumn("event_date", F.to_date("event_ts"))
    flagged = silver_mod.tag_outliers(df)
    outliers = flagged.where(F.col("quality_flag") == "outlier").collect()
    assert len(outliers) == 1
    assert outliers[0]["value"] == 200.0


# ---------- Delta MERGE idempotency ----------

def test_silver_iot_merge_is_idempotent(spark, tmp_path_factory):
    target_path = tmp_path_factory.mktemp("silver_iot")
    table_name = "silver_iot_test"

    spark.sql(f"DROP TABLE IF EXISTS {table_name}")
    spark.sql(
        f"""
        CREATE TABLE {table_name} (
            event_id        STRING,
            ingestion_ts    TIMESTAMP,
            value           DOUBLE,
            event_date      DATE
        ) USING DELTA
        LOCATION '{target_path}'
        """
    )

    staged = spark.createDataFrame(
        [
            ("e1", "2026-06-19 05:11:11", 1.0, "2026-06-19"),
            ("e2", "2026-06-19 05:11:12", 2.0, "2026-06-19"),
        ],
        schema="event_id STRING, ingestion_ts STRING, value DOUBLE, event_date STRING",
    ).select(
        "event_id",
        F.to_timestamp("ingestion_ts").alias("ingestion_ts"),
        "value",
        F.to_date("event_date").alias("event_date"),
    )

    from delta.tables import DeltaTable

    def merge_once():
        tgt = DeltaTable.forName(spark, table_name)
        (
            tgt.alias("t").merge(
                staged.alias("s"),
                "t.event_id = s.event_id",
            )
            .whenMatchedUpdateAll(condition="s.ingestion_ts > t.ingestion_ts")
            .whenNotMatchedInsertAll()
            .execute()
        )

    merge_once()
    first_count = spark.table(table_name).count()
    merge_once()
    second_count = spark.table(table_name).count()

    assert first_count == 2
    assert second_count == 2
