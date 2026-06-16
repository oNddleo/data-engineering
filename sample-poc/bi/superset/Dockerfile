# Superset with the Trino SQLAlchemy driver baked in (needed by both the
# webserver and the init container to reach iceberg via trino://).
ARG SUPERSET_VERSION=4.1.1
FROM apache/superset:${SUPERSET_VERSION}
USER root
RUN pip install --no-cache-dir trino sqlalchemy-trino
USER superset
