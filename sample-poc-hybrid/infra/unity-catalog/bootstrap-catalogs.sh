#!/usr/bin/env bash
# Create the `hybrid` catalog + bronze/silver/gold schemas in Unity Catalog OSS.
# Idempotent — `CREATE ... IF NOT EXISTS` semantics emulated via list-then-create.
set -euo pipefail

UC_URI=${UC_URI:-http://unity-catalog:8087}
CATALOG=${CATALOG:-hybrid}
S3_BUCKET=${S3_BUCKET:-lakehouse}
UC_BIN=/home/unitycatalog/bin/uc

# Wait for UC API readiness (compose healthcheck already does this; defensive).
for i in $(seq 1 30); do
  if "${UC_BIN}" --server "${UC_URI}" catalog list >/dev/null 2>&1; then
    break
  fi
  echo "[uc-bootstrap] waiting for UC at ${UC_URI}... (${i}/30)"
  sleep 2
done

# Catalog ------------------------------------------------------------
if "${UC_BIN}" --server "${UC_URI}" catalog list | grep -qw "${CATALOG}"; then
  echo "[uc-bootstrap] catalog ${CATALOG} exists"
else
  echo "[uc-bootstrap] creating catalog ${CATALOG}"
  "${UC_BIN}" --server "${UC_URI}" catalog create \
      --name "${CATALOG}" \
      --comment "Hybrid lakehouse POC — IoT + image + video"
fi

# Schemas — bronze / silver / gold -----------------------------------
for schema in bronze silver gold smoke; do
  if "${UC_BIN}" --server "${UC_URI}" schema list --catalog "${CATALOG}" | grep -qw "${schema}"; then
    echo "[uc-bootstrap] schema ${CATALOG}.${schema} exists"
  else
    echo "[uc-bootstrap] creating schema ${CATALOG}.${schema}"
    "${UC_BIN}" --server "${UC_URI}" schema create \
        --catalog "${CATALOG}" \
        --name "${schema}" \
        --comment "Medallion layer: ${schema}"
  fi
done

echo "[uc-bootstrap] done. Catalogs:"
"${UC_BIN}" --server "${UC_URI}" catalog list
