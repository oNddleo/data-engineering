"""Spark batch job — scan MinIO raw-media/, extract metadata + thumbnail, append to bronze.media_objects.

Reads binary files via Spark's `binaryFile` source, anti-joins against the
existing Delta table on (object_key, etag) so reruns are incremental, then
applies row-level Python UDFs to extract EXIF / ffprobe metadata and
generate a 256x256 PNG thumbnail. Thumbnails are written back to MinIO at
`thumbnails/<sha1[:2]>/<sha1>.png` (deterministic key, idempotent on rerun).

Run:
    spark-submit /opt/hybrid/pipeline/spark_jobs/batch-media-bronze.py \
        --config /opt/hybrid/pipeline/conf/batch-media-bronze.yaml
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

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from lib.spark_session import build_streaming_session

LOG = logging.getLogger("batch-media-bronze")
APP_NAME = "media-bronze-batch"


@dataclass(frozen=True)
class BatchConfig:
    source_path: str        # s3a://lakehouse/raw-media/
    delta_path: str         # s3a://lakehouse/bronze/media_objects
    bucket: str             # lakehouse
    catalog_table: str      # bronze.media_objects
    glob_filter: str        # *.{png,jpg,jpeg,mp4}
    create_table_if_missing: bool


# ----------------------------- schemas ---------------------------------

IMAGE_META_SCHEMA = T.StructType([
    T.StructField("width",    T.IntegerType()),
    T.StructField("height",   T.IntegerType()),
    T.StructField("exif_json", T.StringType()),
    T.StructField("taken_at",  T.StringType()),   # raw EXIF "YYYY:MM:DD HH:MM:SS"
    T.StructField("gps_lat",   T.DoubleType()),
    T.StructField("gps_lon",   T.DoubleType()),
])

VIDEO_META_SCHEMA = T.StructType([
    T.StructField("duration_sec", T.DoubleType()),
    T.StructField("codec",        T.StringType()),
    T.StructField("bitrate",      T.LongType()),
    T.StructField("fps",          T.DoubleType()),
    T.StructField("width",        T.IntegerType()),
    T.StructField("height",       T.IntegerType()),
    T.StructField("ffprobe_json", T.StringType()),
])


# ----------------------------- UDFs ------------------------------------

def _media_type_from_path(path: str) -> str | None:
    p = path.lower()
    if p.endswith((".png", ".jpg", ".jpeg")):
        return "image"
    if p.endswith(".mp4"):
        return "video"
    return None


def _mime_from_path(path: str) -> str | None:
    p = path.lower()
    if p.endswith(".png"):
        return "image/png"
    if p.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if p.endswith(".mp4"):
        return "video/mp4"
    return None


media_type_udf = F.udf(_media_type_from_path, T.StringType())
mime_udf = F.udf(_mime_from_path, T.StringType())


@F.udf(returnType=IMAGE_META_SCHEMA)
def _image_meta_udf(content):
    if content is None:
        return None
    from lib.media_extractors import extract_image_meta
    return extract_image_meta(bytes(content))


@F.udf(returnType=VIDEO_META_SCHEMA)
def _video_meta_udf(content):
    if content is None:
        return None
    from lib.media_extractors import extract_video_meta
    return extract_video_meta(bytes(content))


def _thumbnail_udf_factory(bucket: str):
    @F.udf(returnType=T.StringType())
    def _thumbnail_udf(content, path, kind):
        if content is None or kind is None:
            return None
        from lib.media_extractors import make_thumbnail
        from lib.minio_upload import upload_thumbnail
        body = make_thumbnail(bytes(content), kind=kind)
        if body is None:
            return None
        return upload_thumbnail(bucket, path, body)
    return _thumbnail_udf


# ----------------------------- pipeline --------------------------------

def load_config(path: str) -> BatchConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return BatchConfig(
        source_path=data["source_path"],
        delta_path=data["delta_path"],
        bucket=data["bucket"],
        catalog_table=data["catalog_table"],
        glob_filter=data.get("glob_filter", "*.{png,jpg,jpeg,mp4}"),
        create_table_if_missing=bool(data.get("create_table_if_missing", True)),
    )


def ensure_bronze_table(spark: SparkSession, cfg: BatchConfig) -> None:
    if not cfg.create_table_if_missing:
        return
    catalog, _table = cfg.catalog_table.rsplit(".", 1)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}")
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.catalog_table} (
            object_key      STRING,
            etag            STRING,
            bucket          STRING,
            media_type      STRING,
            mime            STRING,
            size_bytes      BIGINT,
            modified_at     TIMESTAMP,
            image_meta      STRUCT<width:INT,height:INT,exif_json:STRING,taken_at:STRING,gps_lat:DOUBLE,gps_lon:DOUBLE>,
            video_meta      STRUCT<duration_sec:DOUBLE,codec:STRING,bitrate:BIGINT,fps:DOUBLE,width:INT,height:INT,ffprobe_json:STRING>,
            thumbnail_key   STRING,
            ingestion_ts    TIMESTAMP,
            ingest_date     DATE
        )
        USING DELTA
        PARTITIONED BY (ingest_date)
        LOCATION '{cfg.delta_path}'
        TBLPROPERTIES (
            'delta.columnMapping.mode' = 'name',
            'delta.minReaderVersion'   = '3',
            'delta.minWriterVersion'   = '7'
        )
        """
    )


def list_existing_keys(spark: SparkSession, cfg: BatchConfig) -> DataFrame:
    """Return (object_key, etag) of already-ingested rows for the anti-join."""
    if not spark.catalog.tableExists(cfg.catalog_table):
        return spark.createDataFrame([], schema="object_key STRING, etag STRING")
    return spark.table(cfg.catalog_table).select("object_key", "etag").distinct()


def run(cfg: BatchConfig) -> int:
    spark = build_streaming_session(APP_NAME, stop_gracefully_on_shutdown=False)
    spark.sparkContext.setLogLevel("WARN")
    LOG.info("config=%s", cfg)

    ensure_bronze_table(spark, cfg)

    raw = (
        spark.read.format("binaryFile")
        .option("pathGlobFilter", cfg.glob_filter)
        .option("recursiveFileLookup", "true")
        .load(cfg.source_path)
    )

    # Object key relative to bucket root: strip s3a://<bucket>/ prefix.
    bucket_prefix = f"s3a://{cfg.bucket}/"
    raw = raw.withColumn(
        "object_key",
        F.when(F.col("path").startswith(bucket_prefix),
               F.expr(f"substring(path, {len(bucket_prefix) + 1})"))
         .otherwise(F.col("path")),
    )

    # Etag in binaryFile output is `modificationTime` — we use it as a
    # change-detection proxy since MinIO etags aren't exposed by binaryFile.
    # Concatenate `length` so two writes within the same second to the same
    # key produce different etags (avoids the same-second collision flagged
    # in code-review C2).
    raw = raw.withColumn(
        "etag",
        F.concat_ws("-", F.date_format("modificationTime", "yyyyMMddHHmmss"), F.col("length").cast("string")),
    )

    existing = list_existing_keys(spark, cfg)
    incremental = raw.join(existing, on=["object_key", "etag"], how="left_anti")

    enriched = (
        incremental
        .withColumn("media_type", media_type_udf(F.col("object_key")))
        .where(F.col("media_type").isNotNull())
        .withColumn("mime", mime_udf(F.col("object_key")))
        .withColumn(
            "image_meta",
            F.when(F.col("media_type") == "image", _image_meta_udf(F.col("content"))),
        )
        .withColumn(
            "video_meta",
            F.when(F.col("media_type") == "video", _video_meta_udf(F.col("content"))),
        )
        .withColumn(
            "thumbnail_key",
            _thumbnail_udf_factory(cfg.bucket)(
                F.col("content"), F.col("object_key"), F.col("media_type"),
            ),
        )
        .withColumn("size_bytes", F.col("length"))
        .withColumn("modified_at", F.col("modificationTime"))
        .withColumn("bucket", F.lit(cfg.bucket))
        .withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("ingest_date", F.to_date(F.current_timestamp()))
        .select(
            "object_key", "etag", "bucket", "media_type", "mime",
            "size_bytes", "modified_at",
            "image_meta", "video_meta",
            "thumbnail_key", "ingestion_ts", "ingest_date",
        )
    )

    (
        enriched.write.format("delta")
        .mode("append")
        .partitionBy("ingest_date")
        .save(cfg.delta_path)
    )
    total = spark.read.format("delta").load(cfg.delta_path).count()
    LOG.info("done. total bronze rows now = %d", total)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch media metadata bronze.")
    default_cfg = os.environ.get(
        "BATCH_CONFIG",
        "/opt/hybrid/pipeline/conf/batch-media-bronze.yaml",
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
