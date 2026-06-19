"""Load `devices` + `locations` dimensions from postgres-oltp via JDBC.

Returns small bounded DataFrames the silver builders join with
`F.broadcast()`. The Postgres connection details come from env vars so
the same module works both inside docker-compose (postgres-oltp:5432)
and from a host venv if you ever run silver locally.
"""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def _read(spark: SparkSession, query: str) -> DataFrame:
    url = os.environ.get("PG_OLTP_JDBC_URL", "jdbc:postgresql://postgres-oltp:5432/devices")
    user = os.environ.get("PG_OLTP_USER", "oltpuser")
    password = os.environ.get("PG_OLTP_PASSWORD", "oltppass")
    return (
        spark.read.format("jdbc")
        .option("url", url)
        .option("user", user)
        .option("password", password)
        .option("driver", "org.postgresql.Driver")
        .option("query", query)
        .load()
    )


def load_devices(spark: SparkSession) -> DataFrame:
    """device_id → device_model, owner_org, install_date, fw_version."""
    return _read(
        spark,
        """
        SELECT device_id, model AS device_model, owner_org AS device_owner_org,
               install_date, fw_version AS device_fw_version
        FROM devices
        """,
    )


def load_locations(spark: SparkSession) -> DataFrame:
    """location_id → city + district + lat/lon centroid."""
    return _read(
        spark,
        """
        SELECT location_id, city AS location_city, district AS location_district,
               lat AS location_lat, lon AS location_lon
        FROM locations
        """,
    )


def load_device_locations(spark: SparkSession) -> DataFrame:
    """device_id → location_id (1:1 in the POC seeder, latest assignment wins)."""
    return _read(
        spark,
        """
        SELECT DISTINCT ON (device_id) device_id, location_id, assigned_from
        FROM device_location
        ORDER BY device_id, assigned_from DESC
        """,
    )


def load_device_enrichment(spark: SparkSession) -> DataFrame:
    """Single broadcast-friendly DataFrame: device_id + all dim columns."""
    devices = load_devices(spark)
    locations = load_locations(spark)
    dev_loc = load_device_locations(spark)
    return (
        devices.join(dev_loc, on="device_id", how="left")
        .join(locations, on="location_id", how="left")
        .drop("location_id", "assigned_from")
    )
