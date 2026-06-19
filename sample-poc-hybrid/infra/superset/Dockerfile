ARG SUPERSET_IMAGE_TAG=4.1.2
FROM apache/superset:${SUPERSET_IMAGE_TAG}

USER root

# Superset 4.1 ships without the Trino dialect. Add the official
# sqlalchemy driver so the Trino connection registered by bootstrap.sh
# can be queried from SQL Lab + datasets + dashboards.
RUN pip install --no-cache-dir \
        "trino[sqlalchemy]==0.330.0" \
        "psycopg2-binary==2.9.9"

USER superset
