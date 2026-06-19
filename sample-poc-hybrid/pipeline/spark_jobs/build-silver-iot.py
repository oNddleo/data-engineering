"""Build silver.iot_readings (latest-per-event_id) + silver.iot_anomalies.

Reads bronze.iot_events for the trailing N days, deduplicates by event_id,
normalizes units to SI, joins device + location dimensions from
postgres-oltp (broadcast), tags outliers by per-(device, sensor, day) 3σ
window, then MERGEs into silver. Outlier rows are also appended to a
separate `silver.iot_anomalies` Delta table for alerting.

Run:
    spark-submit /opt/hybrid/pipeline/spark_jobs/build-silver-iot.py \
        --config /opt/hybrid/pipeline/conf/build-silver-iot.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from delta.tables import DeltaTable  # type: ignore[import-untyped]
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import Window
from pyspark.sql import functions as F

from lib.dim_loader import load_device_enrichment
from lib.spark_session import build_streaming_session
from lib.unit_normalizer import to_si_value_udf

LOG = logging.getLogger("build-silver-iot")
APP_NAME = "silver-iot-build"

OUTLIER_SIGMAS = 3.0


@dataclass(frozen=True)
class SilverConfig:
    bronze_table: str            # bronze.iot_events
    target_table: str            # silver.iot_readings
    anomalies_table: str         # silver.iot_anomalies
    target_path: str             # s3a://lakehouse/silver/iot_readings
    anomalies_path: str          # s3a://lakehouse/silver/iot_anomalies
    incremental_days: int
    create_tables_if_missing: bool


def load_config(path: str) -> SilverConfig:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return SilverConfig(
        bronze_table=d["bronze_table"],
        target_table=d["target_table"],
        anomalies_table=d["anomalies_table"],
        target_path=d["target_path"],
        anomalies_path=d["anomalies_path"],
        incremental_days=int(d.get("incremental_days", 7)),
        create_tables_if_missing=bool(d.get("create_tables_if_missing", True)),
    )


def ensure_tables(spark: SparkSession, cfg: SilverConfig) -> None:
    if not cfg.create_tables_if_missing:
        return
    catalog = cfg.target_table.split(".", 1)[0]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.target_table} (
            event_id          STRING,
            device_id         STRING,
            sensor_type       STRING,
            value             DOUBLE,
            value_si          DOUBLE,
            unit              STRING,
            lat               DOUBLE,
            lon               DOUBLE,
            event_ts          TIMESTAMP,
            ingestion_ts      TIMESTAMP,
            device_model      STRING,
            device_owner_org  STRING,
            device_fw_version STRING,
            location_city     STRING,
            location_district STRING,
            quality_flag      STRING,
            event_date        DATE
        )
        USING DELTA
        PARTITIONED BY (event_date)
        LOCATION '{cfg.target_path}'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.columnMapping.mode'   = 'name',
            'delta.minReaderVersion'     = '3',
            'delta.minWriterVersion'     = '7'
        )
        """
    )
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.anomalies_table} (
            event_id     STRING,
            device_id    STRING,
            sensor_type  STRING,
            value        DOUBLE,
            value_si     DOUBLE,
            unit         STRING,
            event_ts     TIMESTAMP,
            ingestion_ts TIMESTAMP,
            quality_flag STRING,
            event_date   DATE
        )
        USING DELTA
        PARTITIONED BY (event_date)
        LOCATION '{cfg.anomalies_path}'
        TBLPROPERTIES (
            'delta.columnMapping.mode' = 'name'
        )
        """
    )


def read_bronze(spark: SparkSession, cfg: SilverConfig) -> DataFrame:
    return spark.table(cfg.bronze_table).where(
        F.col("ingest_date") >= F.expr(f"current_date() - INTERVAL {cfg.incremental_days} DAYS")
    )


def dedup_and_typecast(bronze: DataFrame) -> DataFrame:
    typed = bronze.withColumn("event_ts", F.to_timestamp("ts")).withColumn(
        "event_date", F.to_date("event_ts")
    )
    w = Window.partitionBy("event_id").orderBy(F.col("ingestion_ts").desc())
    return typed.withColumn("_rn", F.row_number().over(w)).where(F.col("_rn") == 1).drop("_rn")


def tag_outliers(deduped: DataFrame) -> DataFrame:
    stats = (
        deduped.groupBy("device_id", "sensor_type", "event_date")
        .agg(F.avg("value").alias("_mean"), F.stddev("value").alias("_std"))
    )
    joined = deduped.join(stats, on=["device_id", "sensor_type", "event_date"], how="left")
    return joined.withColumn(
        "quality_flag",
        F.when(
            F.col("_std").isNotNull() & (F.col("_std") > 0)
            & (F.abs(F.col("value") - F.col("_mean")) > F.lit(OUTLIER_SIGMAS) * F.col("_std")),
            F.lit("outlier"),
        ).otherwise(F.lit("ok")),
    ).drop("_mean", "_std")


def enrich(spark: SparkSession, df: DataFrame) -> DataFrame:
    dim = load_device_enrichment(spark)
    joined = df.join(F.broadcast(dim), on="device_id", how="left")
    return joined.withColumn(
        "quality_flag",
        F.when(
            (F.col("quality_flag") == "ok") & F.col("device_model").isNull(),
            F.lit("missing_dim"),
        ).otherwise(F.col("quality_flag")),
    )


def build_staged(spark: SparkSession, cfg: SilverConfig) -> DataFrame:
    bronze = read_bronze(spark, cfg)
    deduped = dedup_and_typecast(bronze)
    flagged = tag_outliers(deduped)
    enriched = enrich(spark, flagged)
    return enriched.withColumn("value_si", to_si_value_udf("sensor_type", "unit", "value")).select(
        "event_id", "device_id", "sensor_type", "value", "value_si", "unit",
        "lat", "lon", "event_ts", "ingestion_ts",
        "device_model", "device_owner_org", "device_fw_version",
        "location_city", "location_district",
        "quality_flag", "event_date",
    )


def merge_silver(spark: SparkSession, cfg: SilverConfig, staged: DataFrame) -> None:
    target = DeltaTable.forName(spark, cfg.target_table)
    (
        target.alias("t").merge(
            staged.alias("s"),
            "t.event_id = s.event_id",
        )
        .whenMatchedUpdateAll(condition="s.ingestion_ts > t.ingestion_ts")
        .whenNotMatchedInsertAll()
        .execute()
    )


def append_anomalies(cfg: SilverConfig, staged: DataFrame) -> None:
    anomalies = staged.where(F.col("quality_flag") == "outlier").select(
        "event_id", "device_id", "sensor_type", "value", "value_si", "unit",
        "event_ts", "ingestion_ts", "quality_flag", "event_date",
    )
    (
        anomalies.write.format("delta")
        .mode("append")
        .partitionBy("event_date")
        .save(cfg.anomalies_path)
    )


def run(cfg: SilverConfig) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")
    ensure_tables(spark, cfg)

    staged = build_staged(spark, cfg).cache()
    try:
        merge_silver(spark, cfg, staged)
        append_anomalies(cfg, staged)
        LOG.info("silver iot rows staged in this run = %d", staged.count())
    finally:
        staged.unpersist()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Silver IoT build.")
    default_cfg = os.environ.get(
        "SILVER_IOT_CONFIG",
        "/opt/hybrid/pipeline/conf/build-silver-iot.yaml",
    )
    p.add_argument("--config", default=default_cfg)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cfg = load_config(args.config)
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
