"""StructType definition for the IoT bronze stream.

Mirrors `source/schemas/iot-event.schema.json`. Used by `from_json` in
PERMISSIVE mode so payloads that fail to parse become rows with a populated
`_rescued_data` column, which the streaming job tees off to the DLQ topic
without crashing.

Module name is snake_case because it is imported by streaming-iot-bronze.py;
Python's `import` cannot resolve a hyphenated identifier.
"""

from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
)

IOT_EVENT_SCHEMA: StructType = StructType(
    [
        StructField("event_id",    StringType(), nullable=False),
        StructField("device_id",   StringType(), nullable=False),
        StructField("sensor_type", StringType(), nullable=False),
        StructField("value",       DoubleType(), nullable=False),
        StructField("unit",        StringType(), nullable=False),
        StructField("lat",         DoubleType(), nullable=True),
        StructField("lon",         DoubleType(), nullable=True),
        StructField("ts",          StringType(), nullable=False),
        StructField("fw_version",  StringType(), nullable=True),
    ]
)

# Required (NOT NULL) fields — any NULL here triggers DLQ routing in the
# bronze stream's valid/invalid split.
REQUIRED_FIELDS = (
    "event_id",
    "device_id",
    "sensor_type",
    "value",
    "unit",
    "ts",
)

# Columns the bronze write must materialize on top of the parsed event.
# Kept here so tests and the streaming job agree on the contract.
BRONZE_AUDIT_COLUMNS = (
    "ingestion_ts",
    "ingest_date",
    "kafka_topic",
    "kafka_partition",
    "kafka_offset",
)
