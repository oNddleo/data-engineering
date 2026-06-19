"""Thin boto3 wrapper used by media bronze to upload thumbnails.

Kept executor-side friendly:
- Lazy client construction so workers re-create the connection per task.
- Endpoint + credentials read from env vars (passed via spark-env in
  docker-compose so executors see them).
"""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache

import boto3  # type: ignore[import-untyped]

LOG = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    endpoint = os.environ.get("S3_ENDPOINT_URL", "http://minio:9000")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )


def upload_thumbnail(bucket: str, source_object_key: str, body: bytes) -> str | None:
    """Upload a thumbnail keyed by the SHA1 of `source_object_key`.

    Returns the destination key on success, None on failure. Deterministic
    naming means rerunning the bronze job overwrites the same key instead
    of accumulating duplicates.
    """
    if body is None:
        return None
    digest = hashlib.sha1(source_object_key.encode("utf-8")).hexdigest()
    dest_key = f"thumbnails/{digest[:2]}/{digest}.png"
    try:
        _client().put_object(
            Bucket=bucket,
            Key=dest_key,
            Body=body,
            ContentType="image/png",
        )
        return dest_key
    except Exception as e:  # noqa: BLE001
        LOG.warning("thumbnail upload failed (key=%s): %s", source_object_key, e)
        return None
