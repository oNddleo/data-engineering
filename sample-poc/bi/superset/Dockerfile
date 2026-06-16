# Superset with the Trino SQLAlchemy driver baked in (needed by both the
# webserver and the init container to reach iceberg via trino://).
ARG SUPERSET_VERSION=4.1.1
FROM apache/superset:${SUPERSET_VERSION}
USER root
# trino/sqlalchemy-trino: query Iceberg via Trino. psycopg2-binary: the Postgres
# metadata DB driver — required now that superset_config.py points the metadata DB
# at the shared Postgres (the stock image only ships the SQLite default).
RUN pip install --no-cache-dir trino sqlalchemy-trino psycopg2-binary
# Wire the metadata DB to the shared Postgres. /app/pythonpath is on PYTHONPATH,
# so Superset auto-imports this as `superset_config` for BOTH init and webserver.
COPY bi/superset/superset_config.py /app/pythonpath/superset_config.py
USER superset
