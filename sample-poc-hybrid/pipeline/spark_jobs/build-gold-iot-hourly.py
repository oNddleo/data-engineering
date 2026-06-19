"""Build gold.iot_hourly_metrics from silver.iot_readings.

Aggregates avg / min / max / p95 / count + outlier_count per
(device_id, sensor_type, hour). MERGEs into the target so re-runs over
overlapping windows are idempotent.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from delta.tables import DeltaTable  # type: ignore[import-untyped]
from pyspark.sql import functions as F

from lib.spark_session import build_streaming_session

LOG = logging.getLogger("build-gold-iot-hourly")
APP_NAME = "gold-iot-hourly"


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(cfg: dict) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")

    catalog = cfg["target_table"].split(".", 1)[0]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg['target_table']} (
            device_id        STRING,
            sensor_type      STRING,
            hour_ts          TIMESTAMP,
            avg_value_si     DOUBLE,
            min_value        DOUBLE,
            max_value        DOUBLE,
            p95_value        DOUBLE,
            sample_count     BIGINT,
            outlier_count    BIGINT,
            location_city    STRING,
            device_owner_org STRING,
            hour_date        DATE
        )
        USING DELTA
        PARTITIONED BY (hour_date)
        LOCATION '{cfg['target_path']}'
        """
    )

    days = int(cfg.get("incremental_days", 7))
    silver = (
        spark.table(cfg["silver_table"])
        .where(F.col("event_date") >= F.expr(f"current_date() - INTERVAL {days} DAYS"))
        .withColumn("hour_ts", F.date_trunc("hour", "event_ts"))
        .withColumn("hour_date", F.to_date("hour_ts"))
    )

    staged = silver.groupBy(
        "device_id", "sensor_type", "hour_ts", "location_city", "device_owner_org", "hour_date",
    ).agg(
        F.avg("value_si").alias("avg_value_si"),
        F.min("value").alias("min_value"),
        F.max("value").alias("max_value"),
        F.expr("percentile_approx(value, 0.95)").alias("p95_value"),
        F.count("*").alias("sample_count"),
        F.sum(F.when(F.col("quality_flag") == "outlier", 1).otherwise(0)).alias("outlier_count"),
    )

    target = DeltaTable.forName(spark, cfg["target_table"])
    (
        target.alias("t").merge(
            staged.alias("s"),
            "t.device_id = s.device_id AND t.sensor_type = s.sensor_type AND t.hour_ts = s.hour_ts",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
    LOG.info("done. staged rows = %d", staged.count())
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gold IoT hourly metrics.")
    default_cfg = os.environ.get(
        "GOLD_IOT_HOURLY_CONFIG",
        "/opt/hybrid/pipeline/conf/build-gold-iot-hourly.yaml",
    )
    p.add_argument("--config", default=default_cfg)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return run(load_config(args.config))


if __name__ == "__main__":
    sys.exit(main())
