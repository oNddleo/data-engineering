# ADR-002 — OSS Spark + Delta locally instead of Databricks Community Edition

**Status:** Accepted.
**Date:** 2026-06-19 (Validation Session 1, Q1).

## Context

Three deployment options were on the table:

1. OSS Spark 4.0 + Delta Lake 4.0 run via `docker-compose` on a laptop.
2. Databricks Community Edition (free, hosted notebooks).
3. Hybrid — develop locally, ship a Databricks Asset Bundle YAML for production.

## Decision

Use **option 1 — OSS Spark + Delta local via docker-compose**.

## Rationale

- The reference architecture is multi-tier (Kafka KRaft, MinIO, Postgres, Trino, Superset, Airflow). Databricks Community Edition can't reach a local Kafka or MinIO; it would force a stub.
- A laptop POC matches the existing `sample-poc` style — one tarball, one `make demo`, no cloud account required.
- Bitnami's Spark 4.0 image lets us bake Delta 4.0 + Kafka connector + UC client + Postgres JDBC into a deterministic image; no Databricks runtime drift.

## Consequences

- The streaming-as-an-Airflow-DAG pattern is an accepted POC tradeoff (see ADR-004) — Databricks Jobs continuous mode would have been a cleaner fit.
- Unity Catalog OSS is included as the `uc` compose profile for Spark-only experiments, but Trino 470's Delta connector doesn't speak UC yet, so HMS is the primary catalog (Validation Session 2).
- A future production migration likely moves to **Databricks Asset Bundles** for the spark-submit jobs and **K8s Deployment** for the streaming job.
