"""Build gold.device_health — small dimensional summary of every device.

Overwrite-full each run (table is tiny: 1 row per device). Surfaces
last_seen lag and 24h anomaly rate so the Superset dashboard can colour
rows by health.
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

from pyspark.sql import functions as F

from lib.spark_session import build_streaming_session

LOG = logging.getLogger("build-gold-device-health")
APP_NAME = "gold-device-health"


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(cfg: dict) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")

    catalog = cfg["target_table"].split(".", 1)[0]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")

    silver = spark.table(cfg["silver_table"])
    now = F.current_timestamp()

    last_seen = silver.groupBy("device_id").agg(F.max("event_ts").alias("last_seen_ts"))
    recent = silver.where(
        F.col("event_ts") >= F.expr("current_timestamp() - INTERVAL 24 HOURS")
    ).groupBy("device_id").agg(
        F.count("*").alias("events_24h"),
        F.sum(F.when(F.col("quality_flag") == "outlier", 1).otherwise(0)).alias("outliers_24h"),
        F.first("device_model").alias("device_model"),
        F.first("device_owner_org").alias("device_owner_org"),
        F.first("location_city").alias("location_city"),
    )

    health = last_seen.join(recent, on="device_id", how="left").select(
        "device_id",
        "device_model",
        "device_owner_org",
        "location_city",
        "last_seen_ts",
        F.coalesce("events_24h", F.lit(0)).alias("events_24h"),
        F.coalesce("outliers_24h", F.lit(0)).alias("outliers_24h"),
        (
            F.when(F.col("events_24h") > 0, F.col("outliers_24h") / F.col("events_24h"))
            .otherwise(F.lit(None))
        ).alias("anomaly_rate_24h"),
        (
            F.unix_timestamp(now) - F.unix_timestamp(F.col("last_seen_ts"))
        ).cast("long").alias("lag_seconds"),
    )

    (
        health.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .option("path", cfg["target_path"])
        .saveAsTable(cfg["target_table"])
    )
    LOG.info("done. device count = %d", health.count())
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gold device health.")
    default_cfg = os.environ.get(
        "GOLD_DEVICE_HEALTH_CONFIG",
        "/opt/hybrid/pipeline/conf/build-gold-device-health.yaml",
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
