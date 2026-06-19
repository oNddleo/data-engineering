"""Build silver.media_catalog from bronze.media_objects.

- Dedup by object_key, keep the row with the newest etag.
- Extract device_id from the key pattern dev-NNNN-<ulid>.<ext>.
- Broadcast-join devices + locations from postgres-oltp.
- Convert EXIF taken_at string ("YYYY:MM:DD HH:MM:SS") to TIMESTAMP.
- MERGE INTO silver.media_catalog.
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

LOG = logging.getLogger("build-silver-media")
APP_NAME = "silver-media-build"

# Match the device_id only when it is the *terminal* path segment of the
# object key, e.g. `raw-media/image/2026/06/19/dev-0042-<ulid>.jpg`.
# Anchored so a directory called `archive-of-dev-0001/` (or any other
# non-trailing occurrence of `dev-NNNN`) can't poison the join.
DEVICE_ID_REGEX = r"/(dev-\d{4})-[^/]+$"


@dataclass(frozen=True)
class MediaSilverConfig:
    bronze_table: str
    target_table: str
    target_path: str
    create_tables_if_missing: bool


def load_config(path: str) -> MediaSilverConfig:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return MediaSilverConfig(
        bronze_table=d["bronze_table"],
        target_table=d["target_table"],
        target_path=d["target_path"],
        create_tables_if_missing=bool(d.get("create_tables_if_missing", True)),
    )


def ensure_table(spark: SparkSession, cfg: MediaSilverConfig) -> None:
    if not cfg.create_tables_if_missing:
        return
    catalog = cfg.target_table.split(".", 1)[0]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.target_table} (
            object_key        STRING,
            etag              STRING,
            bucket            STRING,
            media_type        STRING,
            mime              STRING,
            size_bytes        BIGINT,
            modified_at       TIMESTAMP,
            taken_at          TIMESTAMP,
            duration_sec      DOUBLE,
            width             INT,
            height            INT,
            gps_lat           DOUBLE,
            gps_lon           DOUBLE,
            thumbnail_key     STRING,
            device_id         STRING,
            device_model      STRING,
            device_owner_org  STRING,
            location_city     STRING,
            location_district STRING,
            ingestion_ts      TIMESTAMP,
            taken_date        DATE
        )
        USING DELTA
        PARTITIONED BY (taken_date)
        LOCATION '{cfg.target_path}'
        TBLPROPERTIES (
            'delta.columnMapping.mode' = 'name'
        )
        """
    )


def build_staged(spark: SparkSession, cfg: MediaSilverConfig) -> DataFrame:
    bronze = spark.table(cfg.bronze_table)
    w = Window.partitionBy("object_key").orderBy(F.col("etag").desc(), F.col("ingestion_ts").desc())
    deduped = bronze.withColumn("_rn", F.row_number().over(w)).where(F.col("_rn") == 1).drop("_rn")

    flattened = deduped.select(
        "object_key", "etag", "bucket", "media_type", "mime",
        "size_bytes", "modified_at",
        F.col("image_meta.taken_at").alias("_taken_at_str"),
        F.col("image_meta.gps_lat").alias("gps_lat"),
        F.col("image_meta.gps_lon").alias("gps_lon"),
        F.col("video_meta.duration_sec").alias("duration_sec"),
        F.coalesce(F.col("image_meta.width"), F.col("video_meta.width")).alias("width"),
        F.coalesce(F.col("image_meta.height"), F.col("video_meta.height")).alias("height"),
        "thumbnail_key", "ingestion_ts",
    )

    with_device = flattened.withColumn(
        "device_id", F.regexp_extract(F.col("object_key"), DEVICE_ID_REGEX, 1)
    ).withColumn(
        "device_id", F.when(F.col("device_id") == "", None).otherwise(F.col("device_id"))
    )

    with_time = with_device.withColumn(
        "taken_at",
        F.to_timestamp("_taken_at_str", "yyyy:MM:dd HH:mm:ss"),
    ).withColumn(
        "taken_date",
        # Fall through current_date so taken_date is never NULL — otherwise
        # NULL would land in __HIVE_DEFAULT_PARTITION__ and show up as a
        # ghost partition in Superset (review H3).
        F.coalesce(F.to_date("taken_at"), F.to_date("modified_at"), F.current_date()),
    ).drop("_taken_at_str")

    dim = load_device_enrichment(spark).select(
        "device_id", "device_model", "device_owner_org", "location_city", "location_district",
    )
    enriched = with_time.join(F.broadcast(dim), on="device_id", how="left")

    return enriched.select(
        "object_key", "etag", "bucket", "media_type", "mime",
        "size_bytes", "modified_at", "taken_at",
        "duration_sec", "width", "height", "gps_lat", "gps_lon",
        "thumbnail_key", "device_id",
        "device_model", "device_owner_org", "location_city", "location_district",
        "ingestion_ts", "taken_date",
    )


def merge_silver(spark: SparkSession, cfg: MediaSilverConfig, staged: DataFrame) -> None:
    target = DeltaTable.forName(spark, cfg.target_table)
    (
        target.alias("t").merge(
            staged.alias("s"),
            "t.object_key = s.object_key",
        )
        .whenMatchedUpdateAll(condition="s.etag <> t.etag OR s.ingestion_ts > t.ingestion_ts")
        .whenNotMatchedInsertAll()
        .execute()
    )


def run(cfg: MediaSilverConfig) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")
    ensure_table(spark, cfg)

    staged = build_staged(spark, cfg).cache()
    try:
        merge_silver(spark, cfg, staged)
        LOG.info("silver media rows staged = %d", staged.count())
    finally:
        staged.unpersist()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Silver media build.")
    default_cfg = os.environ.get(
        "SILVER_MEDIA_CONFIG",
        "/opt/hybrid/pipeline/conf/build-silver-media.yaml",
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
