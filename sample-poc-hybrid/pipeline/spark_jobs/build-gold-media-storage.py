"""Build gold.media_storage_daily — storage usage rollup per (date, media_type).

Source is silver.media_catalog. Emits file count, total bytes, and the
top-5 devices by file count for the day.
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

LOG = logging.getLogger("build-gold-media-storage")
APP_NAME = "gold-media-storage"


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
            dt              DATE,
            media_type      STRING,
            file_count      BIGINT,
            total_bytes     BIGINT,
            top_device_id   STRING,
            top_device_files INT,
            top_devices     ARRAY<STRUCT<device_id:STRING,files:INT>>
        )
        USING DELTA
        PARTITIONED BY (dt)
        LOCATION '{cfg['target_path']}'
        """
    )

    silver = spark.table(cfg["silver_table"])

    per_device = (
        silver.groupBy("taken_date", "media_type", "device_id")
        .agg(F.count("*").cast("int").alias("files"))
    )
    w = Window.partitionBy("taken_date", "media_type").orderBy(F.col("files").desc())
    ranked = per_device.withColumn("_rn", F.row_number().over(w)).where(F.col("_rn") <= 5)
    top_devices = (
        ranked.groupBy("taken_date", "media_type")
        .agg(F.collect_list(F.struct("device_id", "files")).alias("top_devices"))
    )

    totals = silver.groupBy("taken_date", "media_type").agg(
        F.count("*").alias("file_count"),
        F.sum("size_bytes").alias("total_bytes"),
    )

    # Surface the top device as scalar columns alongside the ARRAY so
    # Superset table charts render without JSON-unpacking (review H4).
    top_one = (
        ranked.where(F.col("_rn") == 1).select(
            "taken_date", "media_type",
            F.col("device_id").alias("top_device_id"),
            F.col("files").alias("top_device_files"),
        )
    )
    staged = (
        totals.join(top_devices, ["taken_date", "media_type"], "left")
        .join(top_one, ["taken_date", "media_type"], "left")
        .withColumnRenamed("taken_date", "dt")
    )

    target = DeltaTable.forName(spark, cfg["target_table"])
    (
        target.alias("t").merge(
            staged.alias("s"),
            "t.dt = s.dt AND t.media_type = s.media_type",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
    LOG.info("done. staged rows = %d", staged.count())
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gold media storage rollup.")
    default_cfg = os.environ.get(
        "GOLD_MEDIA_STORAGE_CONFIG",
        "/opt/hybrid/pipeline/conf/build-gold-media-storage.yaml",
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
