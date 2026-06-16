# POC: Rust-Accelerated End-to-End Lakehouse — task runner
# Run `make help` for the list. Targets grow per phase; Phase 1 = infra only.

SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Phase 1: infrastructure ──────────────────────────────────
.PHONY: env
env: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "created .env (edit secrets before prod use)")

.PHONY: up
up: env ## Start the full stack (detached)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the stack (keep volumes)
	$(COMPOSE) down

.PHONY: reset
reset: ## Stop the stack AND wipe all volumes (clean slate)
	$(COMPOSE) down -v

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs (use: make logs SVC=trino)
	$(COMPOSE) logs -f $(SVC)

.PHONY: stats
stats: ## Live resource usage (RAM/CPU) of running containers
	docker stats

.PHONY: smoke
smoke: ## Phase 1 acceptance: create demo schema + verify a parquet lands in MinIO
	$(COMPOSE) exec -T trino trino --execute "$$(cat infra/trino/smoke_test.sql)"
	@echo "--- objects under s3://$${S3_BUCKET:-warehouse} ---"
	$(COMPOSE) exec -T minio sh -c 'mc alias set local http://minio:9000 $$MINIO_ROOT_USER $$MINIO_ROOT_PASSWORD >/dev/null 2>&1; mc ls -r local/$${S3_BUCKET:-warehouse} | head'

.PHONY: trino-cli
trino-cli: ## Open an interactive Trino shell
	$(COMPOSE) exec trino trino

# ── Phase 2: source synthetic data ───────────────────────────
.PHONY: seed-deps
seed-deps: ## Install Python deps for the seeder (into a local venv)
	python3 -m venv .venv-seed && .venv-seed/bin/pip install -q -r source/requirements.txt

.PHONY: seed-full
seed-full: ## Apply schema + bulk-seed baseline e-commerce data
	.venv-seed/bin/python source/seed_source_data.py --mode full

.PHONY: seed-append
seed-append: ## Append a delta (new orders + updated rows) to prove incremental ELT
	.venv-seed/bin/python source/seed_source_data.py --mode append

# ── Phase 3-4: pipeline (ingest + transform) ─────────────────
.PHONY: pipe-deps
pipe-deps: ## Install Python deps for the pipeline (polars, pyiceberg, ...)
	python3 -m venv .venv && .venv/bin/pip install -q -r pipeline/requirements.txt

PY := .venv/bin/python
PIPE := cd pipeline &&

.PHONY: ingest-bronze
ingest-bronze: ## Extract source delta -> Iceberg bronze (append-only)
	$(PIPE) ../$(PY) extract_load_bronze.py $(ARGS)

.PHONY: ingest-bronze-full
ingest-bronze-full: ## Reset bronze and reload everything
	$(PIPE) ../$(PY) extract_load_bronze.py --full

.PHONY: transform-silver
transform-silver: ## Bronze -> silver (dedup latest-per-PK + clean)
	$(PIPE) ../$(PY) transform_silver.py

.PHONY: transform-gold
transform-gold: ## Silver -> gold marts
	$(PIPE) ../$(PY) transform_gold.py

.PHONY: test
test: ## Run transform unit tests (no stack needed)
	$(PY) -m pytest tests/ -q

.PHONY: pipeline
pipeline: ingest-bronze transform-silver transform-gold ## Full ELT: bronze -> silver -> gold

# ── Phase 5-6: full stack (Airflow + Superset) ───────────────
.PHONY: up-full
up-full: env ## Start the FULL stack incl. Airflow + Superset (heavier, ~12GB RAM)
	$(COMPOSE) --profile full up -d --build

.PHONY: down-full
down-full: ## Stop the full stack (keep volumes)
	$(COMPOSE) --profile full down

.PHONY: dag-trigger
dag-trigger: ## Trigger the Airflow ELT DAG (ARGS='--conf {"full_reload":true}' for full)
	$(COMPOSE) exec airflow-scheduler airflow dags trigger lakehouse_elt $(ARGS)

.PHONY: airflow-ui
airflow-ui: ## Print the Airflow UI URL
	@echo "Airflow UI: http://localhost:8082  (admin/admin)"

.PHONY: superset-ui
superset-ui: ## Print the Superset UI URL
	@echo "Superset UI: http://localhost:8088  (admin/admin)"

# ── Phase 7: demo + acceptance ───────────────────────────────
.PHONY: demo
demo: ## End-to-end happy path: boot full -> seed -> full run -> append -> incremental run
	$(MAKE) up-full
	@echo "waiting for stack to settle..." && sleep 30
	$(MAKE) seed-deps seed-full
	$(MAKE) pipe-deps pipeline
	$(MAKE) seed-append
	$(MAKE) pipeline
	$(MAKE) superset-ui airflow-ui
	@echo "demo complete — open Superset and explore iceberg.gold.*"
