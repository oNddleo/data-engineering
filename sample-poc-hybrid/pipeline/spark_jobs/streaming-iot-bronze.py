"""Spark Structured Streaming bronze ingestion for IoT events.

Reads Kafka `iot.sensors`, parses JSON in PERMISSIVE mode, splits valid
events to the Delta table `bronze.iot_events` and unparseable records to
the Kafka DLQ topic `iot.sensors.dlq`. Runs as a continuously-restarting
long-running job; checkpoints under `s3a://<bucket>/_checkpoints/...`
guarantee at-least-once delivery across restarts.

Run:
    spark-submit /opt/hybrid/pipeline/spark_jobs/streaming-iot-bronze.py \
        --config /opt/hybrid/pipeline/conf/streaming-iot-bronze.yaml

Stop:
    SIGTERM to the driver; `spark.streaming.stopGracefullyOnShutdown=true`
    (set by the session builder) drains the current micro-batch first.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `from lib.X import Y` whether the script is invoked as a file path
# or as a module by spark-submit.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from functools import reduce

from lib.dlq_writer import write_dlq
from lib.iot_schema import IOT_EVENT_SCHEMA, REQUIRED_FIELDS
from lib.spark_session import build_streaming_session

LOG = logging.getLogger("streaming-iot-bronze")

APP_NAME = "iot-bronze-stream"


@dataclass(frozen=True)
class StreamConfig:
    bootstrap_servers: str
    source_topic: str
    dlq_topic: str
    delta_path: str
    checkpoint_path: str
    catalog_table: str
    starting_offsets: str
    max_offsets_per_trigger: int
    trigger_interval: str
    create_table_if_missing: bool


def load_config(path: str) -> StreamConfig:
    """Tiny YAML-ish loader: accepts strict JSON to avoid PyYAML dependency.

    The shipping `conf/streaming-iot-bronze.yaml` is JSON-compatible (no
    block-scalar tricks). Drop in PyYAML later if we need richer syntax.
    """
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return StreamConfig(
        bootstrap_servers=data["bootstrap_servers"],
        source_topic=data["source_topic"],
        dlq_topic=data["dlq_topic"],
        delta_path=data["delta_path"],
        checkpoint_path=data["checkpoint_path"],
        catalog_table=data["catalog_table"],
        starting_offsets=data.get("starting_offsets", "earliest"),
        max_offsets_per_trigger=int(data.get("max_offsets_per_trigger", 10_000)),
        trigger_interval=data.get("trigger_interval", "10 seconds"),
        create_table_if_missing=bool(data.get("create_table_if_missing", True)),
    )


def ensure_bronze_table(spark: SparkSession, cfg: StreamConfig) -> None:
    """Create the bronze schema + Delta external table if absent.

    Idempotent. Sets deletion-vector reader/writer versions and column
    mapping=name so future renames don't break readers.
    """
    if not cfg.create_table_if_missing:
        return
    catalog, table = cfg.catalog_table.rsplit(".", 1)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.catalog_table} (
            event_id        STRING,
            device_id       STRING,
            sensor_type     STRING,
            value           DOUBLE,
            unit            STRING,
            lat             DOUBLE,
            lon             DOUBLE,
            ts              STRING,
            fw_version      STRING,
            kafka_topic     STRING,
            kafka_partition INT,
            kafka_offset    BIGINT,
            ingestion_ts    TIMESTAMP,
            ingest_date     DATE
        )
        USING DELTA
        PARTITIONED BY (ingest_date)
        LOCATION '{cfg.delta_path}'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.columnMapping.mode'   = 'name',
            'delta.minReaderVersion'     = '3',
            'delta.minWriterVersion'     = '7'
        )
        """
    )


def build_raw_stream(spark: SparkSession, cfg: StreamConfig) -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", cfg.bootstrap_servers)
        .option("subscribe", cfg.source_topic)
        .option("startingOffsets", cfg.starting_offsets)
        .option("maxOffsetsPerTrigger", str(cfg.max_offsets_per_trigger))
        .option("failOnDataLoss", "false")
        .load()
    )


def parse_batch(batch_df: DataFrame) -> DataFrame:
    """Add a `payload` struct + audit columns. NULL `payload.event_id` ⇒ corrupt."""
    return batch_df.select(
        F.col("value").cast("string").alias("_raw_value"),
        F.col("topic").alias("kafka_topic"),
        F.col("partition").cast("int").alias("kafka_partition"),
        F.col("offset").cast("long").alias("kafka_offset"),
        F.from_json(F.col("value").cast("string"), IOT_EVENT_SCHEMA).alias("payload"),
    )


def _all_required_present() -> "F.Column":
    """Build `payload.f1 IS NOT NULL AND payload.f2 IS NOT NULL AND ...`."""
    checks = [F.col(f"payload.{f}").isNotNull() for f in REQUIRED_FIELDS]
    return reduce(lambda a, b: a & b, checks)


def select_valid(parsed: DataFrame) -> DataFrame:
    return parsed.where(_all_required_present()).select(
        F.col("payload.event_id").alias("event_id"),
        F.col("payload.device_id").alias("device_id"),
        F.col("payload.sensor_type").alias("sensor_type"),
        F.col("payload.value").alias("value"),
        F.col("payload.unit").alias("unit"),
        F.col("payload.lat").alias("lat"),
        F.col("payload.lon").alias("lon"),
        F.col("payload.ts").alias("ts"),
        F.col("payload.fw_version").alias("fw_version"),
        F.col("kafka_topic"),
        F.col("kafka_partition"),
        F.col("kafka_offset"),
        F.current_timestamp().alias("ingestion_ts"),
        F.to_date(F.current_timestamp()).alias("ingest_date"),
    )


def select_invalid(parsed: DataFrame) -> DataFrame:
    """Rows that fail any required-field check — fully unparsed or partial."""
    return parsed.where(~_all_required_present()).select(
        F.col("_raw_value"),
        F.col("kafka_offset"),
    )


def make_batch_handler(cfg: StreamConfig):
    """Build a foreachBatch handler.

    The Delta write uses `txnAppId` + `txnVersion=batch_id` so that a retry
    of the same micro-batch (e.g. after a Kafka DLQ write failure causes
    Spark to re-invoke the handler) becomes a no-op instead of producing
    duplicate rows. This is Delta's recommended idempotency pattern for
    foreachBatch sinks.
    """

    def handle(batch_df: DataFrame, batch_id: int) -> None:
        parsed = parse_batch(batch_df)
        parsed.cache()
        try:
            valid_df = select_valid(parsed)
            (
                valid_df.write.format("delta")
                .mode("append")
                .partitionBy("ingest_date")
                .option("txnAppId", APP_NAME)
                .option("txnVersion", str(batch_id))
                .save(cfg.delta_path)
            )

            invalid_df = select_invalid(parsed)
            published = write_dlq(
                invalid_df,
                bootstrap_servers=cfg.bootstrap_servers,
                topic=cfg.dlq_topic,
            )
            if published:
                LOG.warning("batch %s: invalid records routed to DLQ", batch_id)
        finally:
            parsed.unpersist()

    return handle


def run(cfg: StreamConfig) -> int:
    spark = build_streaming_session(APP_NAME)
    spark.sparkContext.setLogLevel("WARN")
    LOG.info("config=%s", cfg)

    ensure_bronze_table(spark, cfg)

    raw = build_raw_stream(spark, cfg)

    query = (
        raw.writeStream.foreachBatch(make_batch_handler(cfg))
        .outputMode("append")
        .option("checkpointLocation", cfg.checkpoint_path)
        .trigger(processingTime=cfg.trigger_interval)
        .queryName(APP_NAME)
        .start()
    )

    LOG.info(
        "stream started — source=%s sink=%s checkpoint=%s",
        cfg.source_topic, cfg.delta_path, cfg.checkpoint_path,
    )
    query.awaitTermination()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Spark Structured Streaming IoT bronze.")
    default_cfg = os.environ.get(
        "STREAM_CONFIG",
        "/opt/hybrid/pipeline/conf/streaming-iot-bronze.yaml",
    )
    p.add_argument("--config", default=default_cfg, help="Path to JSON-compatible YAML config.")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = load_config(args.config)
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
