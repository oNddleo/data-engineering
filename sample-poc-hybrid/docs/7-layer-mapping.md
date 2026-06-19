# 7-Layer Mapping — POC ↔ Reference Architecture

The reference design lives in [`../../knowledge/architecture-layer-diagram.md`](../../knowledge/architecture-layer-diagram.md). Below is how each tier is realised (or intentionally skipped) in `sample-poc-hybrid`.

| Layer | Reference idea | POC realisation | Status |
|-------|----------------|-----------------|--------|
| **L1 — Sources** | CRM/ERP, OLTP DBs, files/streams, EDMS | Synthetic IoT simulator (`source/iot-simulator.py`), Pillow/ffmpeg media uploader (`source/media-uploader.py`), Postgres OLTP devices/locations (`source/seed-oltp.py`) | ✅ |
| **L2 — Integration** | API Gateway (Kong/APISIX), Kafka, CDC (Debezium/Airbyte) | Kafka 4.0 KRaft single node, S3 PUT for media. No API gateway, no Debezium. | ✅ partial |
| **L3 — Lakehouse / Compute** | Airflow/Dagster, MinIO/S3, Iceberg, Spark/Trino, ClickHouse/StarRocks | Airflow 3.0 (3 DAGs), MinIO, **Delta Lake 4.0** (instead of Iceberg), Spark 4.0 (ETL + streaming) + Trino 470 (query). No OLAP warehouse — Trino federates straight to Delta. | ✅ |
| **L4 — Governance** | OpenMetadata, Great Expectations, Marquez | Delta `enableChangeDataFeed` + `columnMapping.mode=name` + deletion vectors; quality_flag column in silver. GE planned in Phase 9 but the suite scaffold is light. No OpenMetadata. | 🟡 partial |
| **L5 — EDMS** | Mayan/Alfresco, Tika/Unstructured | **Out of scope** — POC stores raw images/videos in MinIO `raw-media/` directly; EDMS integration is left to the production plan. | ❌ |
| **L6 — Security** | Keycloak/OIDC, OPA + Ranger | MinIO IAM (default `minioadmin`), Postgres password auth. No SSO, no row/column policies. Static `.env` creds intentionally — POC only. | ❌ |
| **L7 — Presentation** | Superset/Metabase, Trino Query Gateway | Trino 470 as federated query gateway; Superset 4.1 connects via `trino[sqlalchemy]`. Dashboards built interactively in SQL Lab (no pre-baked YAML). | ✅ |

## Notes

- Choice of **Delta Lake** over Iceberg is documented in `decisions/001-delta-vs-iceberg.md`.
- The **HMS-vs-UC** swap (UC OSS demoted to an experimental profile) is documented in `plan.md` → Validation Session 2.
- Streaming-on-Airflow is an accepted POC tradeoff: `decisions/004-streaming-on-airflow-poc-accepted-tradeoff.md`.
- ML inference over media is intentionally omitted: `decisions/003-no-ml-inference-in-poc.md`.

## What a production-grade follow-up would add

1. OpenMetadata + lineage hooks on every Spark write.
2. Keycloak SSO + Ranger or OPA policies for column-level access on `silver.iot_readings`.
3. EDMS adapter so `raw-media/` is sourced from Mayan/Alfresco instead of a synthetic uploader.
4. Multi-region Kafka KRaft cluster (3 controllers) + Schema Registry.
5. Databricks Asset Bundles for the Spark jobs, or K8s Deployment for the streaming job (instead of the Airflow supervisor pattern).
