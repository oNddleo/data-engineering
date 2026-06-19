"""Slow integration smoke — spins ephemeral Kafka + Spark and runs the
bronze stream in Trigger.AvailableNow mode against a fresh Delta path.

Run explicitly:
    pytest -m slow tests/integration/test_smoke_streaming.py

Requires Docker on the host (testcontainers will skip if absent).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

try:
    from testcontainers.kafka import KafkaContainer  # type: ignore[import-untyped]
except Exception:  # noqa: BLE001
    KafkaContainer = None  # type: ignore[assignment]

pytestmark = pytest.mark.slow


@pytest.mark.skipif(KafkaContainer is None, reason="testcontainers[kafka] not installed")
def test_streaming_iot_bronze_ingests_kafka_to_delta(spark, tmp_path_factory):
    delta_path = tmp_path_factory.mktemp("bronze-iot")
    ckpt_path = tmp_path_factory.mktemp("ckpt-iot")

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()

        # Produce 10 deterministic events using confluent_kafka (avoids
        # adding another Producer dependency since requirements include it).
        from confluent_kafka import Producer  # type: ignore[import-untyped]

        producer = Producer({"bootstrap.servers": bootstrap})
        for i in range(10):
            payload = {
                "event_id": f"evt-{i:03d}",
                "device_id": "dev-0042",
                "sensor_type": "temperature",
                "value": 25.0 + i * 0.1,
                "unit": "C",
                "ts": "2026-06-19T05:11:11Z",
            }
            producer.produce("iot.sensors", json.dumps(payload).encode("utf-8"))
        producer.flush(10)

        # Read via Trigger.AvailableNow so the test exits deterministically.
        from pyspark.sql import functions as F

        from lib.iot_schema import IOT_EVENT_SCHEMA

        raw = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", bootstrap)
            .option("subscribe", "iot.sensors")
            .option("startingOffsets", "earliest")
            .load()
        )

        parsed = raw.select(
            F.from_json(F.col("value").cast("string"), IOT_EVENT_SCHEMA).alias("p")
        ).select("p.*")

        query = (
            parsed.writeStream.format("delta")
            .outputMode("append")
            .option("checkpointLocation", str(ckpt_path))
            .trigger(availableNow=True)
            .start(str(delta_path))
        )
        query.awaitTermination(timeout=120)

        df = spark.read.format("delta").load(str(delta_path))
        assert df.count() == 10
        assert df.where(F.col("device_id") == "dev-0042").count() == 10
