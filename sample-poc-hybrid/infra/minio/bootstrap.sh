#!/usr/bin/env sh
# Create the lakehouse bucket and medallion + media + checkpoint prefixes.
# Run once at stack startup via the minio-bootstrap one-shot container.
set -eu

ENDPOINT=${MINIO_ENDPOINT:-http://minio:9000}
USER=${MINIO_ROOT_USER:-minioadmin}
PASS=${MINIO_ROOT_PASSWORD:-minioadmin}
BUCKET=${S3_BUCKET:-lakehouse}

echo "[minio-bootstrap] Setting alias to ${ENDPOINT}"
mc alias set local "${ENDPOINT}" "${USER}" "${PASS}"

# Bucket — mb is idempotent in mc 2024+ but we guard anyway.
if mc ls "local/${BUCKET}" >/dev/null 2>&1; then
  echo "[minio-bootstrap] bucket ${BUCKET} exists"
else
  echo "[minio-bootstrap] creating bucket ${BUCKET}"
  mc mb "local/${BUCKET}"
fi

# Prefixes — created by putting a 0-byte sentinel object (S3 has no
# native "mkdir"; this avoids surprises for Spark writers).
for prefix in bronze silver gold raw-media thumbnails _checkpoints _quality_reports; do
  echo "[minio-bootstrap] ensuring prefix ${BUCKET}/${prefix}/"
  echo "" | mc pipe "local/${BUCKET}/${prefix}/.keep"
done

# Public-read on thumbnails so Superset can render <img src=...> links.
mc anonymous set download "local/${BUCKET}/thumbnails" || true

echo "[minio-bootstrap] done."
mc ls "local/${BUCKET}/"
