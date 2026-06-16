#!/bin/sh
# Create the Iceberg warehouse bucket in MinIO. Iceberg REST will NOT auto-create it.
# Idempotent: --ignore-existing makes re-runs safe.
set -eu

mc alias set local "http://minio:9000" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"
mc mb --ignore-existing "local/${S3_BUCKET}"
# versioning is optional but cheap insurance for a POC
mc version enable "local/${S3_BUCKET}" || true

echo "minio-bootstrap: bucket '${S3_BUCKET}' ready"
