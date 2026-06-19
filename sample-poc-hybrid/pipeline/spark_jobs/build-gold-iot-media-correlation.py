"""Build gold.iot_media_correlation — for each media row, find the IoT event
on the same device closest in time within ±N minutes.

This is the "hybrid" payoff of the POC: it co-locates IoT + multimedia in
one lakehouse so analysts can ask "what did the air-quality sensor read
when this photo was taken?".

As-of join is implemented via a bounded range join + row_number(1) to
avoid blowing up Spark with a true CROSS JOIN.
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
from pyspark.sql import Window
from pyspark.sql import functions as F

from lib.spark_session import build_streaming_session

LOG = logging.getLogger("build-gold-iot-media-correlation")
APP_NAME = "gold-iot-media-correlation"


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
            object_key             STRING,
            media_type             STRING,
            device_id              STRING,
            taken_at               TIMESTAMP,
            thumbnail_key          STRING,
            nearest_event_id       STRING,
            nearest_event_ts       TIMESTAMP,
            nearest_sensor_type    STRING,
            nearest_value          DOUBLE,
            seconds_between        BIGINT,
            taken_date             DATE
        )
        USING DELTA
        PARTITIONED BY (taken_date)
        LOCATION '{cfg['target_path']}'
        """
    )

    window_seconds = int(cfg.get("window_seconds", 300))

    media = (
        spark.table(cfg["media_table"])
        .where(F.col("taken_at").isNotNull() & F.col("device_id").isNotNull())
        .select(
            "object_key", "media_type", "device_id", "taken_at",
            "thumbnail_key", "taken_date",
        )
    )

    iot = spark.table(cfg["iot_table"]).select(
        F.col("device_id").alias("iot_device_id"),
        F.col("event_id").alias("nearest_event_id"),
        F.col("event_ts").alias("nearest_event_ts"),
        F.col("sensor_type").alias("nearest_sensor_type"),
        F.col("value").alias("nearest_value"),
    )

    joined = media.alias("m").join(
        iot.alias("i"),
        (F.col("m.device_id") == F.col("i.iot_device_id"))
        & (F.abs(F.unix_timestamp("i.nearest_event_ts") - F.unix_timestamp("m.taken_at")) <= window_seconds),
        "left",
    )

    w = Window.partitionBy("object_key").orderBy(
        F.abs(F.unix_timestamp("nearest_event_ts") - F.unix_timestamp("taken_at"))
    )
    staged = (
        joined.withColumn("_rn", F.row_number().over(w))
        .where(F.col("_rn") == 1)
        .withColumn(
            "seconds_between",
            (F.unix_timestamp("nearest_event_ts") - F.unix_timestamp("taken_at")).cast("long"),
        )
        .select(
            "object_key", "media_type", "device_id", "taken_at",
            "thumbnail_key", "nearest_event_id", "nearest_event_ts",
            "nearest_sensor_type", "nearest_value", "seconds_between", "taken_date",
        )
    )

    target = DeltaTable.forName(spark, cfg["target_table"])
    (
        target.alias("t").merge(
            staged.alias("s"),
            "t.object_key = s.object_key",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
    LOG.info("done. staged rows = %d", staged.count())
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gold IoT-media correlation.")
    default_cfg = os.environ.get(
        "GOLD_IOT_MEDIA_CORR_CONFIG",
        "/opt/hybrid/pipeline/conf/build-gold-iot-media-correlation.yaml",
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
