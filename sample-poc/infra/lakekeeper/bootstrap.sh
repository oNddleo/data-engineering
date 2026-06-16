#!/bin/sh
# Bootstrap Lakekeeper, then register a `warehouse` backed by MinIO (S3, path-style).
# Idempotent: treats "already exists" (409) and "already bootstrapped" (400 typed)
# as success, but FAILS on any other unexpected status instead of swallowing it.
#
# NOTE: Lakekeeper's management API shape is version-sensitive. If a call returns an
# unexpected 4xx, check the running image's /swagger-ui or https://docs.lakekeeper.io
# and adjust the JSON below. This is a Phase-1 acceptance point (must pass on real boot).
set -eu

LK="${LAKEKEEPER_URL:-http://lakekeeper:8181}"

# POST $1=path $2=json — succeed on 2xx, 409 (already exists), and the
# "already bootstrapped" 400 (a successful re-run), fail otherwise.
post_ok() {
  path="$1"; body="$2"
  code=$(curl -s -o /tmp/lk_resp -w "%{http_code}" -X POST "${LK}${path}" \
    -H "Content-Type: application/json" -d "${body}")
  case "${code}" in
    2*) echo "  ${path} -> ${code} ok" ;;
    409) echo "  ${path} -> 409 already exists, continuing" ;;
    # Re-running against an already-initialized catalog: Lakekeeper signals "already
    # done" with 400 + a typed body rather than 409 — CatalogAlreadyBootstrapped for
    # the server bootstrap, and CreateWarehouseStorageProfileOverlap (the warehouse is
    # already registered with this storage) for the warehouse call. Both mean the
    # one-shot already succeeded on a prior run; treat as success so it is idempotent
    # across `up` cycles. Only a genuine, unrecognized 400 should fail.
    400) if grep -qiE "AlreadyBootstrapped|already bootstrapped|already exists|StorageProfileOverlap|overlaps with existing" /tmp/lk_resp; then
           echo "  ${path} -> 400 already done, continuing"
         else
           echo "  ${path} -> 400 UNEXPECTED:"; cat /tmp/lk_resp; echo; return 1
         fi ;;
    *) echo "  ${path} -> ${code} UNEXPECTED:"; cat /tmp/lk_resp; echo; return 1 ;;
  esac
}

echo "lakekeeper-bootstrap: bootstrapping server..."
post_ok "/management/v1/bootstrap" '{"accept-terms-of-use": true}'

echo "lakekeeper-bootstrap: registering warehouse '${LAKEKEEPER_WAREHOUSE}'..."
post_ok "/management/v1/warehouse" "{
  \"warehouse-name\": \"${LAKEKEEPER_WAREHOUSE}\",
  \"storage-profile\": {
    \"type\": \"s3\",
    \"bucket\": \"${S3_BUCKET}\",
    \"key-prefix\": \"iceberg\",
    \"endpoint\": \"${S3_ENDPOINT}\",
    \"region\": \"${S3_REGION}\",
    \"path-style-access\": true,
    \"flavor\": \"minio\",
    \"sts-enabled\": false
  },
  \"storage-credential\": {
    \"type\": \"s3\",
    \"credential-type\": \"access-key\",
    \"aws-access-key-id\": \"${MINIO_ROOT_USER}\",
    \"aws-secret-access-key\": \"${MINIO_ROOT_PASSWORD}\"
  }
}"

echo "lakekeeper-bootstrap: done"
