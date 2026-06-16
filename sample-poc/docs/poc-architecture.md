# POC Architecture — what was built vs the full reference

## Mapping to the 7-layer reference

The source architecture ([../../knowledge/architecture-layer-diagram.md](../../knowledge/architecture-layer-diagram.md))
has 7 layers and ~20 tools. This POC implements a **single vertical slice** through it:

| Reference layer | Full architecture | This POC |
|-----------------|-------------------|----------|
| L1 Sources | CRM/ERP, DBs, files, EDMS | PostgreSQL (synthetic e-commerce) |
| L2 Integration | Kong, Kafka, Debezium, Airbyte | **watermark snapshot ELT** (no Kafka) |
| L3 Lakehouse | Airflow, MinIO, Iceberg, Spark, Trino, ClickHouse | Airflow + MinIO + Iceberg + **Polars** + Trino |
| L4 Governance | OpenMetadata, Great Expectations, Elementary | one reconciliation smoke check only |
| L5 EDMS | Mayan, Tika, Unstructured | — (out of scope) |
| L6 Security | Keycloak, OPA, Ranger | — (open, POC-only) |
| L7 Presentation | Superset, Trino gateway | Superset + Trino |

## Deliberate scope decisions (not silent cuts)

- **CDC deferred.** The architecture lists Debezium CDC. For the lakehouse thesis the POC
  uses watermark-based incremental snapshot ELT instead — it proves the data flow without
  Kafka + Connect (saving ~2GB RAM + 3 containers). CDC is a documented stretch path.
- **No Spark.** Polars (Rust) covers transforms at POC scale; Trino covers query. Spark
  would add JVM weight without proving anything new at this scale.
- **No ClickHouse.** Trino-on-Iceberg satisfies the POC's query need; a dedicated OLAP
  warehouse is a later optimization.
- **Governance reduced** to a single gold-vs-line-revenue reconciliation query (the canary).
  A full quality/lineage stack (OpenMetadata, GE) is a separate follow-on plan.

## The Rust / Python split (honest)

The user chose a "Rust-accelerated" stack. Where Rust is genuinely production-ready in 2026:

- **Lakekeeper** — Iceberg REST catalog, single Rust binary, no JVM. ✅
- **Polars** — source reads (connectorx → Arrow) and ALL transforms (dedup, joins,
  aggregations). The Rust engine does the actual compute. ✅

Where it is **not** ready, so Python fills in:

- **Iceberg writes.** No production pure-Rust Iceberg write/upsert path exists in 2026
  (`iceberg-rust` is append-only/experimental; DataFusion-Iceberg write is experimental).
  All writes go through **PyIceberg**. This is unavoidable, not a shortcut.
- **Orchestration** (Airflow) and **BI** (Superset) are Python; **Trino** is JVM.

So the defensible claim is *"Rust where it is production-ready,"* not *"a pure-Rust stack."*
A lighter alternative — **DuckDB** for read + transform + local query — would prove the same
end-to-end thesis with less plumbing, and is the recommended fallback if the Polars/PyIceberg
split proves fiddly against the running Lakekeeper version.

## Medallion design

- **Bronze** — append-only raw log. Incremental at the *extract* boundary
  (`updated_at > watermark`). No upsert needed → avoids the immature Iceberg merge path.
- **Silver** — latest-per-PK (dedup on `updated_at`) + basic cleaning. This is where the
  append-only log collapses to current state.
- **Gold** — business marts the dashboard consumes (daily revenue, revenue by category,
  top customers, order-status funnel). Recomputed via `overwrite` (small, deterministic).

## Why this proves the thesis

A second ingest after `make seed-append` writes only the watermark delta to bronze
(verifiable via Iceberg snapshot `added-records`), silver dedups it to current state, gold
recomputes, and Trino/Superset reflect the change — one trustworthy path from OLTP row to
dashboard, reproducible from a clean clone.
