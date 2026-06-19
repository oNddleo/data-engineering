"""Phase 1 smoke test: write 1 row to Delta on MinIO via Hive Metastore.

Run via:
    make smoke-hybrid

What it proves:
    1. Spark 4.0 starts with Delta + Hive + S3a jars correctly loaded.
    2. Hive Metastore at thrift://hive-metastore:9083 reachable.
    3. S3a → MinIO write path works (warehouse + table data land in MinIO).
    4. Round-trip read returns the expected row.

Failure modes the script surfaces:
    - Hive metastore unreachable → MetaException on CREATE SCHEMA.
    - MinIO credentials wrong → S3 403 on commit.
    - Delta jar missing → "format(delta) not found" on writer.
"""

from __future__ import annotations

import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


SCHEMA = "smoke"
TABLE = "phase1_handshake"
LOCATION = "s3a://lakehouse/bronze/_smoke/phase1_handshake"


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("phase1-smoke-test")
        .enableHiveSupport()
        .getOrCreate()
    )


def main() -> int:
    spark = build_session()
    spark.sparkContext.setLogLevel("WARN")

    # Schema must exist in HMS before CREATE TABLE; idempotent.
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    spark.sql(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE}")

    df = spark.createDataFrame(
        [("phase1", "kraft-kafka-hms-delta", 1)],
        schema="run_label STRING, components STRING, value INT",
    ).withColumn("event_ts", F.current_timestamp())

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("path", LOCATION)
        .saveAsTable(f"{SCHEMA}.{TABLE}")
    )

    read_back = spark.table(f"{SCHEMA}.{TABLE}")
    count = read_back.count()
    print(f"[smoke] table {SCHEMA}.{TABLE} row count = {count}")
    read_back.show(truncate=False)

    if count != 1:
        print(f"[smoke] FAIL: expected 1 row, got {count}", file=sys.stderr)
        return 1

    print("[smoke] OK — Spark 4.0 + Delta 4.0 + HMS 4.0 + MinIO handshake verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
