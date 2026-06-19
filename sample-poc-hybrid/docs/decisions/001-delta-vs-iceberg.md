# ADR-001 — Delta Lake over Apache Iceberg

**Status:** Accepted.
**Date:** 2026-06-19 (Validation Session 1).

## Context

The reference architecture in `knowledge/architecture-layer-diagram.md` calls out **Apache Iceberg** as the table format. Our sibling POC `sample-poc` already builds on Iceberg via Lakekeeper + PyIceberg. The hybrid POC needed to pick a format too — same or different.

## Decision

Use **Delta Lake 4.0** as the lakehouse table format throughout `sample-poc-hybrid`.

## Rationale

1. **Databricks alignment.** The POC's brief — "mô phỏng Databricks" — implies Databricks-native primitives. Delta + the Spark Delta extension + Unity Catalog OSS map 1:1 onto what a Databricks runtime gives you. Iceberg here would force a parallel set of choices and obscure the Databricks-style story.
2. **Structured Streaming maturity.** Spark Structured Streaming → Delta is the best-trodden path for the IoT pipeline. Iceberg streaming sinks exist but require more careful checkpoint + watermark wiring.
3. **Change Data Feed + deletion vectors.** Delta 4.0 ships both with sensible defaults; gives us per-row history for free in silver MERGE-driven flows.
4. **Coexistence with `sample-poc`.** Running both POCs side-by-side shows the same medallion shape on two different table formats — useful for comparing operability and trade-offs in the project changelog.

## Consequences

- Trino's connector is `delta_lake` with `hive.metastore=thrift`. UC OSS for Delta-from-Trino isn't ready as of Trino 470 (see Validation Session 2 + code-review C1 in Phase 1) — HMS is the primary catalog instead.
- Maintenance is `OPTIMIZE … ZORDER` + `VACUUM RETAIN N HOURS` (Delta vocabulary), not Iceberg's `expire_snapshots` / `rewrite_data_files`.
- Tests use `delta-spark==4.0.0` packaging — no Iceberg jars in the Spark image.

## Reversibility

Switching to Iceberg would require: new connector for Trino, replace Delta CTAS DDL across all bronze/silver/gold scripts, replace MERGE INTO semantics with `MERGE` (Iceberg syntax differs slightly), and rewire Airflow DAGs to call the new entry scripts. Estimated 2–3 days of work; not done lightly.
