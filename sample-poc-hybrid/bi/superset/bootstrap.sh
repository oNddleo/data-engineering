#!/usr/bin/env bash
# Superset 4.1 bootstrap — DB migration, admin user, Trino connection.
#
# Designed to run inside the superset container as the entrypoint (or via
# `docker compose exec superset bash bootstrap.sh`). Idempotent; safe to
# rerun after image rebuilds.
set -euo pipefail

ADMIN_USER=${SUPERSET_ADMIN_USER:-admin}
ADMIN_PASSWORD=${SUPERSET_ADMIN_PASSWORD:-admin}
ADMIN_EMAIL=${SUPERSET_ADMIN_EMAIL:-admin@example.com}
TRINO_HOST=${TRINO_HOST:-trino}
TRINO_PORT=${TRINO_PORT:-8080}
TRINO_USER=${TRINO_USER:-trino}
TRINO_CATALOG=${TRINO_CATALOG:-delta}

echo "[superset] db upgrade..."
superset db upgrade

echo "[superset] init roles + perms..."
superset init

echo "[superset] ensuring admin user $ADMIN_USER..."
superset fab create-admin \
    --username "$ADMIN_USER" \
    --firstname admin --lastname admin \
    --email "$ADMIN_EMAIL" \
    --password "$ADMIN_PASSWORD" || true

# Register the Trino database via Superset's CLI shell. The CLI shell evaluates
# arbitrary Python against the live Superset metadata DB, which is the
# supported way to register a connection from a script in Superset 4.x.
SQLALCHEMY_URI="trino://${TRINO_USER}@${TRINO_HOST}:${TRINO_PORT}/${TRINO_CATALOG}"
echo "[superset] registering Trino database $SQLALCHEMY_URI..."
superset shell <<EOF
from superset import db
from superset.models.core import Database

name = "Trino (Delta Lakehouse)"
existing = db.session.query(Database).filter_by(database_name=name).first()
if existing is None:
    db.session.add(
        Database(
            database_name=name,
            sqlalchemy_uri="$SQLALCHEMY_URI",
            expose_in_sqllab=True,
            allow_run_async=True,
            allow_ctas=True,
            allow_cvas=True,
            allow_dml=False,
        )
    )
    db.session.commit()
    print("[superset] created Trino connection")
else:
    print("[superset] Trino connection already exists, skipping")
EOF

echo "[superset] bootstrap done."
