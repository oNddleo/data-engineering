ARG AIRFLOW_IMAGE_TAG=3.0.6
FROM apache/airflow:${AIRFLOW_IMAGE_TAG}

USER root

# docker CLI so DAG tasks can `docker exec` into spark-master.
# The host's /var/run/docker.sock is bind-mounted into this container by
# docker-compose; we just need the client binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
