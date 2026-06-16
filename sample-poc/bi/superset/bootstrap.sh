#!/bin/bash
# Initialize Superset and register Trino as a database connection.
# Runs once (superset-init container). Idempotent-ish: re-running is safe.
set -eu

pip install --no-cache-dir trino sqlalchemy-trino >/dev/null 2>&1 || true

superset db upgrade

superset fab create-admin \
  --username "${SUPERSET_ADMIN:-admin}" \
  --firstname Admin --lastname User \
  --email admin@example.com \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true

superset init

# Register Trino (iceberg catalog) as a Superset database.
superset set-database-uri \
  --database_name trino-iceberg \
  --uri "trino://admin@trino:8080/iceberg" || \
  echo "set-database-uri failed — add it manually in the UI (Data > Databases)."

echo "superset-bootstrap: done. UI at http://localhost:8088 (admin/admin)"
