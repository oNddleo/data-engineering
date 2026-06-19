# Project Overview & PDR — Hybrid Lakehouse POC

## Problem Statement

The enterprise 7-layer reference architecture (in [`../knowledge/architecture-layer-diagram.md`](../../knowledge/architecture-layer-diagram.md)) defines a medallion-structured lakehouse pattern — bronze → silver → gold — for a single payload class (OLTP e-commerce). This POC proves the pattern scales to **multiple concurrent payload types** (IoT telemetry streams, images, videos) on the **same table format, compute engine, and orchestration stack**, eliminating the need for separate ingest paths per domain.

## Scope

**In Scope:**
- Extend the 7-layer architecture to ingest **3 new payload classes** via **Apache Spark 4.0 + Delta Lake 4.0** (Databricks-aligned stack on docker-compose).
- **IoT streaming:** Kafka 4.0 KRaft (no Zookeeper) → Spark Structured Streaming → Delta Bronze table.
- **Image & Video batch ingest:** MinIO S3-compatible storage → Python extractors (Pillow EXIF, ffprobe metadata) → Delta Bronze.
- **Medallion pattern:** bronze (raw) → silver (dedup, cleansing, enrichment) → gold (domain marts).
- **Orchestration:** Airflow 3.0 LocalExecutor with 3 DAGs (streaming supervisor, hourly batch, daily maintenance).
- **Query & BI:** Trino 470 (Delta connector) + Superset 4.1 dashboards.
- **Catalog:** Hive Metastore 4.0 (primary); Unity Catalog OSS 0.3 available via `uc` profile (Spark-only).
- **Testing:** unit tests (pure functions) + smoke integration test (testcontainers Kafka).
- **Code standards:** JSON-compatible YAML configs, pure-function libraries, idempotency via Delta MERGE semantics.

**Out of Scope:**
- EDMS (Layer 5) integration.
- Real CDC (Change Data Capture) from production systems — synthetic via Faker.
- ML inference (YOLO/Whisper on images/videos) — deferred to v2.
- Multi-tenant security, Keycloak, Ranger row/column policies.
- Production-grade Kafka HA (uses single combined-mode KRaft node).
- Cloud deployment (bake-off targets laptop, not AWS/Azure).

## Success Criteria

- [ ] `make demo-hybrid` boots full stack (zero state) and completes end-to-end in < 10 minutes.
- [ ] Streaming job sustains ≥ 100 IoT events/second for ≥ 5 minutes without restart.
- [ ] ≥ 50 PNG/JPG images + ≥ 10 MP4 videos extracted to Delta with EXIF/ffprobe metadata + thumbnail.
- [ ] Superset displays ≥ 3 dashboards: IoT real-time gauges, device health status, media storage usage.
- [ ] All unit tests pass; smoke integration test validates data lineage bronze→silver→gold.
- [ ] Trino queries 10,000+ rows from gold marts in < 5 seconds.
- [ ] Code-review action items from all 9 phases applied and documented in Phase 1 consistency sweep.

## Stakeholders

| Role | Responsibility |
|------|-----------------|
| **Architect** | Validate 7-layer pattern extensibility; confirm medallion shape fits all 3 payload classes. |
| **Data Eng Lead** | Design bronze → silver → gold contract; define idempotency & MERGE strategies. |
| **Platform Eng** | Maintain docker-compose stack; ensure reproducibility on laptop. |
| **QA / Tester** | Run make demo-hybrid; validate against Success Criteria. |
| **BI Analyst** | Author Superset dashboards; test Trino query response times. |

## Constraints & Dependencies

**Technical Constraints:**
- Laptop memory: ≥ 14 GB for docker-compose full profile.
- Spark 4.0 requires JDK 17 (not 11); baked into Spark container image.
- Delta Lake 4.0 + Kafka 4.0 must coexist in a single Spark driver JVM.
- Trino 470 OSS does NOT support `delta.metastore=unity` (reversed from Session 1 validation); HMS is primary.

**Upstream Dependencies:**
- Plan inherits medallion shape + Airflow scheduling patterns from sibling `sample-poc` (Rust/Polars/Iceberg).
- Reuses Postgres OLTP schema patterns from knowledge base.

**Downstream Dependencies:**
- Production migration would require K8s deployment, Databricks Job API, and Unity Catalog upstream tracking (v2 roadmap).

## Key Decisions

See [`docs/decisions/`](decisions/) for architecture decision records (ADRs):
- **ADR-001:** Delta Lake over Iceberg (Databricks alignment, Structured Streaming maturity, CDF + deletion vectors).
- **ADR-002:** OSS Spark + docker-compose over Databricks Community Edition (local Kafka + MinIO unreachable from CE).
- **ADR-003:** No ML inference in POC (model serving deferred; bronze stores binary + thumbnail in Delta).
- **ADR-004:** Streaming-on-Airflow accepted as POC tradeoff (production should use K8s Deployment or Databricks Job continuous).

## Metrics & Validation

**Functional Metrics:**
- End-to-end latency: < 10 minutes from zero state to first dashboard query.
- Streaming throughput: 100+ events/second sustained.
- Data freshness: hourly gold marts, daily device health snapshots.

**Quality Metrics:**
- Test coverage: ≥ 85% unit; ≥ 1 smoke integration per domain (IoT, media).
- Code review: zero critical/high items from adversarial reviews.

**Operational Metrics:**
- Recovery time after volume wipe: `make reset-warehouse` < 2 minutes.
- Trino latency on gold tables: p99 < 5 seconds for 10K row queries.

## Version History

| Date | Status | Notes |
|------|--------|-------|
| 2026-06-19 | Complete | All 9 phases shipped; Validation Log Sessions 1–2 complete. |

---

**Approval:** Validated against plan.md Success Criteria (Session 1–2). Consistency sweep clean.

**Document Version:** 1.0 | **Last Updated:** 2026-06-19
