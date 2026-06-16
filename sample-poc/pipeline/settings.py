"""Environment-driven settings shared across the pipeline.

Defaults assume manual runs FROM THE HOST (localhost). Inside containers
(Airflow, Phase 5) override the hostnames via env: source-db / lakekeeper / minio.
"""
from __future__ import annotations

import os

# --- Source Postgres (connectorx URI for Polars) ---
SOURCE_DB_URI = os.getenv(
    "SOURCE_DB_URI",
    "postgresql://{u}:{p}@{h}:{port}/{db}".format(
        u=os.getenv("SOURCE_DB_USER", "source"),
        p=os.getenv("SOURCE_DB_PASSWORD", "source"),
        h=os.getenv("SOURCE_DB_HOST", "localhost"),
        port=os.getenv("SOURCE_DB_PORT", "5432"),
        db=os.getenv("SOURCE_DB_NAME", "ecommerce"),
    ),
)

# --- Lakekeeper Iceberg REST catalog ---
CATALOG_URI = os.getenv("ICEBERG_CATALOG_URI", "http://localhost:8181/catalog")
CATALOG_WAREHOUSE = os.getenv("ICEBERG_WAREHOUSE", "warehouse")

# --- S3 / MinIO (used by PyIceberg + s3fs) ---
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
S3_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "warehouse")

# --- Medallion namespaces ---
NS_BRONZE = "bronze"
NS_SILVER = "silver"
NS_GOLD = "gold"

# Control prefix for watermark state in the warehouse bucket.
WATERMARK_KEY = os.getenv("WATERMARK_KEY", "_control/watermarks.json")


def s3_properties() -> dict:
    """PyIceberg FileIO properties for MinIO."""
    return {
        "s3.endpoint": S3_ENDPOINT,
        "s3.access-key-id": S3_ACCESS_KEY,
        "s3.secret-access-key": S3_SECRET_KEY,
        "s3.path-style-access": "true",
        "s3.region": S3_REGION,
    }


def s3fs_storage_options() -> dict:
    """fsspec/s3fs options for reading/writing the watermark JSON."""
    return {
        "key": S3_ACCESS_KEY,
        "secret": S3_SECRET_KEY,
        "client_kwargs": {"endpoint_url": S3_ENDPOINT, "region_name": S3_REGION},
    }
