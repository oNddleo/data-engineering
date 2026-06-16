# Rust + Iceberg Lakehouse Maturity Assessment (2026)

**Date:** 2026-06-13  
**Scope:** POC readiness for Postgres CDC → MinIO + Iceberg → Trino → Superset  
**Target:** Rust-accelerated processing with Python orchestration

---

## Executive Summary

Rust + Iceberg in 2026 is **partially production-ready**. Read support is solid; write support is maturing but still lags Java reference. **No pure-Rust write-to-Iceberg path exists for complex workloads.** Pragmatic POC strategy: Rust for compute (Polars, DataFusion), Python for orchestration and writes.

---

## 1. iceberg-rust: READ Production-Ready, WRITE Emerging

**Status:** iceberg-rust 0.9.0 (released March 2026) — 0.8.0 added 144 PRs (Nov 2025–Jan 2026)

### Read Support
✅ **Production-ready** for catalog scanning, table discovery, REST catalog auth.

### Write Support
⚠️ **Experimental** — supports only:
- **FastAppend** (append-only, new manifest per commit)
- **INSERT INTO** with automatic sort-based clustering (0.9.0 feature)
- V2 + V3 metadata formats

### Missing from Iceberg-rust
- ❌ Upsert/MERGE operations
- ❌ Delete operations  
- ❌ Compaction services
- ❌ Full equivalence to Java reference impl (lags 1–2 years)

**Verdict:** Append-only workloads against REST catalog work. Upsert pipelines do NOT.

Sources:
- [Apache Iceberg Rust 0.8.0 Release](https://iceberg.apache.org/blog/apache-iceberg-rust-0.8.0-release/)
- [Apache Iceberg Rust 0.9.0 Release](https://iceberg.apache.org/blog/apache-iceberg-rust-0.9.0-release/)
- [iceberg-rust GitHub Issues #329](https://github.com/apache/iceberg-rust/issues/329)

---

## 2. DataFusion + Iceberg: Read ✅, Write ⚠️

**Status:** iceberg-datafusion crate active; DataFusion Comet experimental.

### Read Support
✅ **Production-ready** — Arrow-native scans, no data reshaping, proven on S3 workloads.

### Write Support
⚠️ **Experimental** — DataFusion Comet uses reflection to extract FileScanTasks from Iceberg; native write operations under active discussion. RisingWave (built on DataFusion) uses embedded Rust compaction engine but does NOT write Iceberg tables directly.

**Verdict:** DataFusion queries Iceberg tables at scale. For writes, still falls back to PyIceberg or Spark.

Sources:
- [Apache Iceberg DataFusion Integration](https://github.com/apache/iceberg-rust/blob/main/crates/integrations/datafusion/README.md)
- [Blazing Fast Iceberg Queries with Apache DataFusion in RisingWave](https://risingwave.com/blog/blazing-fast-iceberg-queries-with-apache-datafusion-in-risingwave/)
- [DataFusion Comet Iceberg Integration](https://datafusion.apache.org/comet/user-guide/latest/iceberg.html)

---

## 3. Polars + Iceberg: Read ✅, Write via PyIceberg ⚠️

**Status:** Polars 1.x (2026)

### Read Support
✅ **Production-ready** — `polars.scan_iceberg()` with lazy evaluation, works with REST catalogs.

### Write Support
- ⚠️ **Streaming writes** added in 2026 (solves in-memory constraint of earlier versions)
- ⚠️ **Method:** Calls PyIceberg under the hood; Polars serializes DataFrame → Arrow → PyIceberg
- ⚠️ Does NOT circumvent PyIceberg dependency

**Contrast with Delta:**  
Polars has native `write_delta()` (no Spark). Iceberg write path requires Java/Python bridge.

Sources:
- [Using DuckDB and Polars to Query Iceberg Tables](https://datalakehousehub.com/blog/2026-05-duckdb-polars-iceberg/)
- [Polars scan_iceberg documentation](https://docs.pola.rs/api/python/dev/reference/api/polars.scan_iceberg.html)
- [Polars Issue #22336 — streaming writes](https://github.com/pola-rs/polars/issues/22336)

---

## 4. delta-rs: Production-Ready for WRITE/UPSERT (But Not Iceberg)

**Status:** delta-rs 0.18.x+ (2026)

### Maturity
✅ **Production-ready** — merge/upsert fully atomic, handles schema evolution, real-world deployments in Jan 2026+.

### Critical Caveat
**This is Delta Lake, NOT Apache Iceberg.** Choosing Rust + delta-rs pushes you OUT of Iceberg format. Not compatible with your mandate.

**Use case:** If Iceberg requirement relaxes → delta-rs eliminates Spark dependency entirely.

Sources:
- [Why MERGE Is Slower Than You Think (Jan 2026)](https://medium.com/@harsh11csb/why-merge-is-slower-than-you-think-and-how-to-design-fast-upsert-pipelines-in-delta-lake-979c45491e0c)
- [Delta Lake Upsert](https://delta.io/blog/delta-lake-upsert/)

---

## 5. Iceberg REST Catalogs: Lakekeeper (Rust) vs Alternatives

| Catalog | Lang | Maturity | Size | Ops |
|---------|------|----------|------|-----|
| **Lakekeeper** | Rust | 0.12.0 (Apr 2026) | ~100MB binary, <50MB RAM | Single binary, no JVM |
| **Polaris** | Rust | Apache TLP (Feb 2026) | Single binary | Vendor-neutral, multi-cloud |
| **Nessie** | Java | Stable | ~500MB | Git-like branching |
| **Tabular** | Java | Commercial | Hosted | Managed option |

**For Laptop POC:**  
✅ **Lakekeeper 0.12.0** — lightweight, Docker-friendly, Apr 2026 release includes audit events + OPA optimization. Single-binary startup in ms.

Sources:
- [The State of Apache Iceberg Catalogs in June 2026](https://amdatalakehouse.substack.com/p/the-state-of-apache-iceberg-catalogs)
- [Lakekeeper Docs](https://docs.lakekeeper.io/)
- [Lakekeeper GitHub Releases](https://github.com/lakekeeper/lakekeeper/releases)

---

## 6. Pragmatic Rust + Python Hybrid for Iceberg POC (2026)

**Realistic division of labor:**

### Use Rust For (Proven ✅)
- **Polars** – transform + exploration (read + append-only writes via PyIceberg)
- **DataFusion** – analytical queries against Iceberg (read-only)
- **Lakekeeper** – catalog server (REST API, no JVM)

### Use Python For (Necessary ⚠️)
- **PyIceberg** – all writes, merges, deletes, schema updates
- **DuckDB** – ACID writes to Iceberg (also uses PyIceberg under hood)
- **Orchestration** – Airflow/Prefect (already planned)

### Use Spark Only If
- Distributed writes across cluster (Iceberg V2+ branch-on-write)
- Complex delete predicates
- Schema evolution at scale

**Honest gap:** Iceberg upsert in pure Rust doesn't exist. You cannot avoid PyIceberg for production Iceberg writes.

---

## 7. Recommended Component Stack for POC

### Catalog
✅ **Lakekeeper 0.12.0 (Rust)** – Docker locally, MinIO backend, REST catalog for all clients.

### Data Processing
- **Read:** Polars (native Iceberg scan) OR DataFusion (SQL)
- **Transform:** Polars (append-only) → PyIceberg write
- **Query:** Trino (native Iceberg) or DataFusion (experimental)

### Orchestration + Writes
- **Python:** PyIceberg (all upserts/deletes), Polars, Airflow

### What NOT to Use
❌ Pure iceberg-rust for writes (not production-ready)  
❌ delta-rs (wrong format)  
❌ Spark (defeats "Rust-accelerated" goal; use only if upsert complexity grows)

---

## Maturity & Risk Assessment

| Component | GA Date | Risk | Gap |
|-----------|---------|------|-----|
| iceberg-rust (read) | 2025 | Low | None |
| iceberg-rust (append) | 0.9.0 (Mar 2026) | Medium | No upsert |
| DataFusion + Iceberg (read) | 2025 | Low | Write experimental |
| Polars + Iceberg (read) | 2025 | Low | Write via PyIceberg |
| delta-rs (write) | 2024 | Low | Wrong format |
| Lakekeeper (REST catalog) | 0.12.0 (Apr 2026) | Low | New; rapid iteration |

---

## Unresolved Questions

1. Will iceberg-rust 0.10.0+ (Q3 2026 projected) stabilize upsert, or remain append-only?
2. Does Lakekeeper 0.12.0 support all REST catalog auth methods (OAuth2, OIDC, API keys) your production requires?
3. If CDC produces high-frequency deletes, will PyIceberg merge performance saturate MinIO network before Rust bottleneck?
4. Are you open to DuckDB as Iceberg write backend (alternative to PyIceberg, also Python bindings)?

---

## Recommendation

**For a low-risk, Rust-forward Iceberg POC in 2026:**

1. **Deploy Lakekeeper 0.12.0** as REST catalog (Docker Compose)
2. **Use Polars** for read + light transforms (native scan)
3. **Fall back to PyIceberg** (Python) for CDC-driven writes/upserts
4. **Use Trino** for query layer (native Iceberg support, not DataFusion)
5. **Orchestrate with Airflow** (Python, proven)

**Why this path:**
- Maximizes Rust where mature (catalog, reads, transforms)
- Avoids immature Rust write path (iceberg-rust)
- Keeps Python for orchestration (already planned)
- No Spark needed (meets cost goal)
- Matches 2026 maturity boundaries

**If upsert frequency << 10/min:** Entire stack works on laptop. If >> 100/min: revisit Spark or DuckDB write strategy.
