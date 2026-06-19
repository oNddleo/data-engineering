SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

ENV_FILE ?= .env
COMPOSE := docker compose --env-file $(ENV_FILE)

.PHONY: help env up-hybrid up-uc up-full down-hybrid clean-hybrid logs ps healthcheck \
        bootstrap-uc smoke-hybrid kafka-topics trino-cli psql-meta psql-oltp \
        kafka-id config-check

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

up-full: env    ## Bring up full stack (HMS + kafka-ui + 2 spark workers)
	$(COMPOSE) --profile full up -d --build

down-hybrid:    ## Stop & remove containers (keep volumes)
	$(COMPOSE) --profile full --profile uc down

clean-hybrid:   ## Stop & remove containers + volumes (DESTRUCTIVE)
	$(COMPOSE) --profile full --profile uc down -v

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
