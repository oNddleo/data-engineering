"""Publish parse-failed Kafka records to the IoT DLQ topic.

We use Spark's built-in Kafka writer (instead of an inline confluent-kafka
producer) so the foreachBatch driver doesn't have to manage a side
connection. The original raw payload bytes are sent verbatim — operators
can replay from `iot.sensors.dlq` once the bug that broke parsing is fixed.
"""

from __future__ import annotations

import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

LOG = logging.getLogger(__name__)


def write_dlq(df: DataFrame, *, bootstrap_servers: str, topic: str) -> bool:
    """Write `df` rows to Kafka. Requires `_raw_value` STRING + `kafka_offset` LONG.

    Keys by `kafka_offset` so DLQ consumers can deduplicate deterministically.
    Returns True if the writer was invoked (rows existed), False otherwise.
    """
    if not _has_rows(df):
        return False

    payload = df.select(
        F.col("kafka_offset").cast("string").alias("key"),
        F.col("_raw_value").cast("string").alias("value"),
    )
    (
        payload.write.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("topic", topic)
        .save()
    )
    LOG.warning("DLQ: published invalid records to %s", topic)
    return True


def _has_rows(df: DataFrame) -> bool:
    """Cheap probe — Spark's `take(1)` short-circuits at the first row."""
    return len(df.take(1)) > 0
