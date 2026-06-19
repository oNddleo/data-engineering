SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

ENV_FILE ?= .env
COMPOSE := docker compose --env-file $(ENV_FILE)

.PHONY: help env up-hybrid up-uc up-full up-airflow down-hybrid clean-hybrid \
        logs ps healthcheck bootstrap-uc smoke-hybrid kafka-topics trino-cli \
        psql-meta psql-oltp kafka-id config-check source-deps seed-iot seed-media \
        seed-oltp seed-all lint-source lint-pipeline lint-dags stream-iot-bronze \
        stop-stream-iot stream-status batch-media-bronze build-silver-iot \
        build-silver-media build-silver maintenance reset-warehouse \
        build-gold-iot-hourly build-gold-device-health build-gold-media-storage \
        build-gold-correlation build-gold airflow-ui airflow-trigger

# Path used by all source/*.py runners; falls back to system python3.
PYTHON ?= python3
RATE   ?= 50
DUR    ?= 60
COUNT  ?= 60
RATIO  ?= 5:1

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

env:            ## Copy .env.example -> .env (idempotent)
	@if [ ! -f $(ENV_FILE) ]; then cp .env.example $(ENV_FILE); echo "Created $(ENV_FILE)"; else echo "$(ENV_FILE) already exists"; fi

kafka-id:       ## Generate a fresh Kafka KRaft cluster UUID
	docker run --rm $${KAFKA_IMAGE:-apache/kafka:4.0.0} /opt/kafka/bin/kafka-storage.sh random-uuid

config-check:   ## Validate docker-compose syntax (no image pull, no run)
	$(COMPOSE) config --quiet && echo "compose config OK"

up-hybrid: env  ## Bring up MVP stack (HMS primary catalog, single worker)
	$(COMPOSE) up -d --build

up-uc: env      ## Bring up stack + Unity Catalog OSS (Spark-only; experimental)
	$(COMPOSE) --profile uc up -d --build

up-full: env    ## Bring up full stack (HMS + kafka-ui + 2 spark workers + Airflow)
	$(COMPOSE) --profile full up -d --build

up-airflow: env ## Add Airflow (api-server + scheduler + dag-processor) to running stack
	$(COMPOSE) --profile airflow up -d --build

down-hybrid:    ## Stop & remove containers (keep volumes)
	$(COMPOSE) --profile full --profile uc down

clean-hybrid:   ## Stop & remove containers + volumes (DESTRUCTIVE)
	$(COMPOSE) --profile full --profile uc down -v

reset-warehouse: ## Drop bronze/silver/gold from HMS + wipe Delta + checkpoints in MinIO
	@echo "Dropping HMS schemas..."
	-$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-sql -e \
	  "DROP SCHEMA IF EXISTS bronze CASCADE; \
	   DROP SCHEMA IF EXISTS silver CASCADE; \
	   DROP SCHEMA IF EXISTS gold   CASCADE; \
	   DROP SCHEMA IF EXISTS smoke  CASCADE;"
	@echo "Wiping MinIO prefixes..."
	-$(COMPOSE) run --rm minio-bootstrap sh -c '\
	  mc alias set local http://minio:9000 $${MINIO_ROOT_USER} $${MINIO_ROOT_PASSWORD} && \
	  mc rm --recursive --force local/$${S3_BUCKET}/bronze/        || true; \
	  mc rm --recursive --force local/$${S3_BUCKET}/silver/        || true; \
	  mc rm --recursive --force local/$${S3_BUCKET}/gold/          || true; \
	  mc rm --recursive --force local/$${S3_BUCKET}/_checkpoints/  || true'
	@echo "reset-warehouse done. raw-media/ and thumbnails/ untouched."

logs:           ## Tail logs for all services
	$(COMPOSE) logs -f --tail=200

ps:             ## Show container status
	$(COMPOSE) ps

healthcheck:    ## Print health status of every running service
	$(COMPOSE) ps --format 'table {{.Service}}\t{{.Status}}'

bootstrap-uc:   ## Re-run Unity Catalog bootstrap (catalog + schemas) — needs `up-uc`
	$(COMPOSE) --profile uc up --no-deps unity-catalog-bootstrap

kafka-topics:   ## List Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list

trino-cli:      ## Open Trino CLI
	$(COMPOSE) exec trino trino --catalog delta

psql-meta:      ## psql into postgres-meta
	$(COMPOSE) exec postgres-meta psql -U $${PG_META_USER} -d $${PG_META_DB}

psql-oltp:      ## psql into postgres-oltp
	$(COMPOSE) exec postgres-oltp psql -U $${PG_OLTP_USER} -d $${PG_OLTP_DB}

smoke-hybrid:   ## Smoke test: spark-submit writes & reads 1 Delta row via HMS
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --master spark://spark-master:7077 \
	  /opt/bitnami/spark/work/smoke-test.py

# --- Phase 2: source / synthetic data generators ---------------------

source-deps:    ## Install Python deps for source/ generators (host venv)
	$(PYTHON) -m pip install -r source/requirements.txt

lint-source:    ## Byte-compile all source/*.py for syntax check
	$(PYTHON) -m compileall -q source

seed-oltp:      ## Seed Postgres OLTP devices DB (idempotent)
	PG_OLTP_HOST=localhost PG_OLTP_PORT=$${PORT_PG_OLTP:-5434} \
	$(PYTHON) source/seed-oltp.py

seed-iot:       ## Produce RATE events/s for DUR seconds to Kafka iot.sensors
	$(PYTHON) source/iot-simulator.py \
	    --bootstrap localhost:$${PORT_KAFKA_CLIENT:-9092} \
	    --rate $(RATE) --duration $(DUR)

seed-media:     ## Upload COUNT media objects (ratio RATIO) to MinIO raw-media/
	S3_ENDPOINT_URL=http://localhost:$${PORT_MINIO_API:-9000} \
	AWS_ACCESS_KEY_ID=$${MINIO_ROOT_USER:-minioadmin} \
	AWS_SECRET_ACCESS_KEY=$${MINIO_ROOT_PASSWORD:-minioadmin} \
	$(PYTHON) source/media-uploader.py --count $(COUNT) --ratio $(RATIO)

seed-all:       ## Run seed-oltp + seed-iot (60s) + seed-media (60 objects)
	$(MAKE) seed-oltp
	$(MAKE) seed-iot DUR=30
	$(MAKE) seed-media COUNT=60

# --- Phase 3: streaming IoT bronze -----------------------------------

lint-pipeline:  ## Byte-compile all pipeline/spark_jobs Python for syntax check
	$(PYTHON) -m compileall -q pipeline/spark_jobs

stream-iot-bronze: ## Start the IoT bronze stream inside spark-master (foreground in container, detached from host)
	$(COMPOSE) exec -d spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name iot-bronze-stream \
	  --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/streaming-iot-bronze.py \
	  --config /opt/hybrid/pipeline/conf/streaming-iot-bronze.yaml

stop-stream-iot: ## SIGTERM the IoT bronze stream JVM driver (graceful — drains last batch)
	$(COMPOSE) exec spark-master bash -c '\
	    pid=$$(pgrep -f "org.apache.spark.deploy.SparkSubmit.*streaming-iot-bronze" | head -n1); \
	    if [ -n "$$pid" ]; then \
	      echo "sending SIGTERM to JVM driver pid=$$pid"; \
	      kill -TERM "$$pid"; \
	      for i in 1 2 3 4 5 6 7 8 9 10; do \
	        kill -0 "$$pid" 2>/dev/null || { echo "driver exited"; exit 0; }; \
	        sleep 1; \
	      done; \
	      echo "driver still running after 10s — escalate manually"; \
	    else \
	      echo "no streaming driver found"; \
	    fi'

stream-status:  ## Show running spark-submit driver processes inside spark-master
	$(COMPOSE) exec spark-master bash -c 'pgrep -fa spark-submit || echo "no spark-submit running"'

# --- Phase 4: media batch bronze -------------------------------------

batch-media-bronze: ## Run the media bronze batch (EXIF/ffprobe + thumbnails → Delta)
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name media-bronze-batch \
	  --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/batch-media-bronze.py \
	  --config /opt/hybrid/pipeline/conf/batch-media-bronze.yaml

# --- Phase 5: silver + maintenance -----------------------------------

build-silver-iot:    ## Build silver.iot_readings + silver.iot_anomalies (incremental 7d)
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name silver-iot-build --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-silver-iot.py \
	  --config /opt/hybrid/pipeline/conf/build-silver-iot.yaml

build-silver-media:  ## Build silver.media_catalog (MERGE INTO from bronze.media_objects)
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name silver-media-build --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-silver-media.py \
	  --config /opt/hybrid/pipeline/conf/build-silver-media.yaml

build-silver:        ## Run both silver builds sequentially
	$(MAKE) build-silver-iot
	$(MAKE) build-silver-media

maintenance:         ## OPTIMIZE (+ZORDER) + VACUUM all medallion tables
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name delta-maintenance --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/maintenance-optimize.py \
	  --config /opt/hybrid/pipeline/conf/maintenance-optimize.yaml

# --- Phase 6: gold marts ---------------------------------------------

build-gold-iot-hourly: ## Hourly IoT metrics per device + sensor
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name gold-iot-hourly --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-gold-iot-hourly.py \
	  --config /opt/hybrid/pipeline/conf/build-gold-iot-hourly.yaml

build-gold-device-health: ## Device health summary (last_seen, lag, anomaly rate)
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name gold-device-health --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-gold-device-health.py \
	  --config /opt/hybrid/pipeline/conf/build-gold-device-health.yaml

build-gold-media-storage: ## Daily media storage rollup by media_type
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name gold-media-storage --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-gold-media-storage.py \
	  --config /opt/hybrid/pipeline/conf/build-gold-media-storage.yaml

build-gold-correlation: ## Cross-domain IoT⇄media nearest-event as-of join
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
	  --name gold-iot-media-correlation --master spark://spark-master:7077 \
	  /opt/hybrid/pipeline/spark_jobs/build-gold-iot-media-correlation.py \
	  --config /opt/hybrid/pipeline/conf/build-gold-iot-media-correlation.yaml

build-gold:          ## Run all 4 gold jobs sequentially
	$(MAKE) build-gold-iot-hourly
	$(MAKE) build-gold-device-health
	$(MAKE) build-gold-media-storage
	$(MAKE) build-gold-correlation

# --- Phase 7: Airflow orchestration ----------------------------------

lint-dags:           ## Byte-compile all orchestration/dags Python for syntax check
	$(PYTHON) -m compileall -q orchestration/dags

airflow-ui:          ## Open Airflow UI URL
	@echo "Airflow UI → http://localhost:$${PORT_AIRFLOW:-8086}"
	@echo "Login → $${AIRFLOW_ADMIN_USER:-admin} / $${AIRFLOW_ADMIN_PASSWORD:-admin}"

airflow-trigger:     ## Trigger an Airflow DAG: make airflow-trigger DAG=hybrid_batch_pipeline
	$(COMPOSE) exec airflow-scheduler airflow dags trigger $(DAG)
