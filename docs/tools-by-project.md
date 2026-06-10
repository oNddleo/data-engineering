# Công cụ & Tech Stack theo Project

> **Phạm vi:** 176 project data engineering trong monorepo
> **Cách trích xuất:** Phân tích từ `README.md` (Stack section), `pyproject.toml`/`requirements.txt`, và `docker-compose.yml` của mỗi project
> **Cập nhật:** 2026-06-10

---

## 1. Cách đọc tài liệu

Mỗi project có 3 trường:

- **Mô tả:** Tóm tắt một câu trích từ README
- **Tools:** Các framework / runtime / database / infra được phát hiện qua keyword detection
- **Docker images:** Các image cụ thể được khai báo trong `docker-compose.yml` (nếu project có)

> ⚠️ *Lưu ý:* Detection theo keyword nên có thể bỏ sót tool ít xuất hiện. Khi cần chi tiết tuyệt đối hãy đọc thẳng `pyproject.toml` hoặc `README.md` của project. `pytest` xuất hiện rất nhiều vì đa số project có test suite — không nhắc lại trong tổng kết để giảm nhiễu.

---

## 2. Tổng kết tần suất Tools (Top 30)

| Tool / Stack | Số project sử dụng | Vai trò chính |
|---|---:|---|
| **Python** | 169 | Ngôn ngữ chính |
| pytest | 135 | Testing framework |
| WebSocket/SSE | 27 | Real-time push UI / API |
| **NumPy** | 23 | Numerical computing |
| **PostgreSQL** | 22 | OLTP database |
| **Pandas** | 21 | DataFrame analytics |
| **FastAPI** | 21 | REST API server |
| **Kafka** | 16 | Message broker / event log |
| **SQLite** | 15 | Embedded database |
| **Parquet/Arrow** | 15 | Columnar storage format |
| **MinIO/S3** | 14 | Object storage |
| **Redis** | 10 | Cache / state store |
| **DuckDB** | 8 | OLAP engine local |
| **Spark** | 7 | Batch processing |
| **BigQuery** | 7 | Cloud DW |
| **sqlglot** | 6 | SQL parser |
| **Prometheus** | 6 | Metrics |
| **Avro** | 6 | Schema serialization |
| **Snowflake** | 5 | Cloud DW |
| **Iceberg** | 5 | Lakehouse table format |
| **Flink** | 5 | Stream processor |
| **dlt** | 5 | Data ingestion |
| **AWS** | 5 | Cloud platform |
| **Airflow** | 5 | Orchestrator |
| **LocalStack** | 4 | AWS local emulator |
| **React** | 3 | Frontend |
| **Grafana** | 3 | Observability |
| **dbt** | 3 | DW transformation |
| **Chart.js** | 3 | Visualization |
| **TimescaleDB** | 2 | Time-series DB |

**Ít gặp nhưng đáng chú ý:** Terraform, Superset, Metabase, Power BI, Memgraph/Neo4j, Databricks, MLflow, OpenTelemetry, ClickHouse, Kestra, Bruin, RocksDB, gRPC, LLVM, TLA+, Cytoscape.js, Streamlit, PyTorch, scikit-learn, MongoDB, MySQL, Hudi, Delta Lake, Dagster, Prefect.

---

## 3. Tools theo từng nhóm Domain

### 3.1 Stack điển hình theo nhóm

| Nhóm | Stack điển hình |
|---|---|
| Streaming & Real-time | Python + Kafka + Redis + FastAPI + WebSocket/SSE + Docker Compose |
| Batch/ETL/Orchestration | Python + Airflow/Dagster/Prefect/Kestra + Postgres/BigQuery + dbt + Docker |
| Data Quality & Governance | Python + Great Expectations/Soda + Kafka + Postgres + Redis + sqlglot + Cytoscape.js |
| Query & Storage Engines | Python (pure) + NumPy + DuckDB + Parquet/Arrow + sqlglot |
| Lakehouse / DW | Spark + MinIO/S3 + Iceberg/Delta + Airflow/Databricks + dbt + Terraform |
| Distributed Systems | Python/Go + TLA+ + gRPC + RocksDB |
| Probabilistic DS | Pure Python + NumPy + pytest |
| VN-specific Pipelines | Python pure + pytest (đa số là MVP toolkit theo domain) |

---

## 4. Danh sách chi tiết theo Project (A–Z)

> Section dài. Tổ chức theo thứ tự alphabetical. Mỗi project có Mô tả + Tools + Docker images (nếu có).

### abandoned-cart-recovery-pipeline
- **Mô tả:** Funnel-event sessionization + abandoned-cart detection + recovery
- **Tools:** Python

### adaptive-microbatch-optimizer
- **Mô tả:** Streaming processor tự điều chỉnh kích thước micro-batch window
- **Tools:** Python, React

### adversarial-chaos-engine
- **Mô tả:** Adversarial fuzzing có chủ đích cho data pipeline
- **Tools:** Python

### airflow_minio_twitter_data_pipeline
- **Mô tả:** Pipeline dữ liệu Twitter dùng Airflow + MinIO (S3-compatible)
- **Tools:** MinIO/S3, Airflow, Docker

### air-quality-iot-pipeline
- **Mô tả:** Monitor chất lượng không khí VN — PM2.5/PM10/NO2/SO2/O3/CO
- **Tools:** Python

### anti-money-laundering-graph
- **Mô tả:** Directed multigraph in-memory + 5 mẫu AML cổ điển
- **Tools:** Python

### api-pagination-handler
- **Mô tả:** Framework pagination REST API (4 strategy)
- **Tools:** Python

### api-rate-limit-orchestrator
- **Mô tả:** Distributed token-bucket rate limiter
- **Tools:** Python, Redis

### aqp-coreset-engine
- **Mô tả:** Approximate query processing dùng coreset weighted samples
- **Tools:** Python, NumPy

### art-mvcc-index
- **Mô tả:** Adaptive Radix Tree (ICDE 2013) + multi-version concurrency control
- **Tools:** Python

### backfill-orchestrator
- **Mô tả:** Orchestrator backfill theo time-partition
- **Tools:** Python

### banking-anomaly-pipeline
- **Mô tả:** Fraud detection real-time trên banking transaction qua Kafka micro-batch
- **Tools:** Python, Kafka, Spark, Redis, FastAPI, Chart.js, WebSocket/SSE
- **Docker images:** `bitnami/kafka:3.6`, `redis:7-alpine`

### bayesian-dq-scorer
- **Mô tả:** DQ scorer — Beta posterior cho mọi chiều chất lượng (completeness/freshness/uniqueness)
- **Tools:** Python, NumPy, Pandas

### b-epsilon-tree
- **Mô tả:** Write-optimized B^ε-tree
- **Tools:** Python

### bft-stream
- **Mô tả:** Byzantine fault-tolerant streaming — PBFT chỉ cho watermark advancement
- **Tools:** Python

### bitcoinMonitor
- **Mô tả:** Near real-time ETL: CoinGecko → SQLite → FastAPI dashboard (MVP)
- **Tools:** Python, SQLite, FastAPI, Chart.js, WebSocket/SSE

### bloom-filter
- **Mô tả:** Bloom filter toolkit production-grade, pure Python
- **Tools:** Python

### cardinality-learned-optimizer
- **Mô tả:** Neo/Bao query optimizer loop cho PostgreSQL — TreeLSTM + Thompson sampling
- **Tools:** Python, PostgreSQL, NumPy, PyTorch
- **Docker images:** `ankane/pgvector:latest`, `postgres:15`

### causal-feature-store
- **Mô tả:** Feature store trả vector causally consistent (per-entity vector clock)
- **Tools:** Python, WebSocket/SSE

### cdc-debezium-postgres-kafka
- **Mô tả:** Toolkit type-safe Python cho path Postgres → Debezium → Kafka
- **Tools:** Python, Kafka, PostgreSQL, Avro
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-schema-registry:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `debezium/connect:2.5`, `debezium/postgres:16`

### cdc-pipeline
- **Mô tả:** CDC production stream mọi INSERT/UPDATE/DELETE từ Postgres WAL
- **Tools:** Python, Kafka, PostgreSQL, Avro
- **Docker images:** `confluentinc/cp-kafka:7.5.0`, `confluentinc/cp-schema-registry:7.5.0`, `confluentinc/cp-zookeeper:7.5.0`, `postgres:15`, `quay.io/debezium/connect:2.5`

### cep-engine
- **Mô tả:** Complex Event Processing in-process sub-millisecond
- **Tools:** Python, NumPy

### chandy-lamport-snapshot
- **Mô tả:** Snapshot phân tán Chandy-Lamport (core của Flink checkpoint)
- **Tools:** Python, Flink, WebSocket/SSE

### change-data-capture
- **Mô tả:** CDC toolkit pure Python
- **Tools:** Python, Kafka

### circuit-breaker-toolkit
- **Mô tả:** Circuit breaker pattern (Fowler / Nygaard)
- **Tools:** Python

### columnar-compression-testbed
- **Mô tả:** Testbed columnar encoding (FSST/ALP/Gorilla) + adaptive per-column selector
- **Tools:** Python, NumPy

### column-encryption-pipeline
- **Mô tả:** Mã hoá cột PII với KMS per-customer keys + live rotation + crypto erasure (GDPR RTBF)
- **Tools:** Python, MinIO/S3, LocalStack, AWS
- **Docker images:** `localstack/localstack:3.4`

### column-statistics-collector
- **Mô tả:** Single-pass column profiler (null/distinct/min/max…)
- **Tools:** Python

### count-min-sketch
- **Mô tả:** Count-Min Sketch probabilistic frequency estimator
- **Tools:** Python

### cow-mor-benchmark
- **Mô tả:** Benchmark Copy-on-Write vs Merge-on-Read trên Parquet/Iceberg-style
- **Tools:** Python, DuckDB, Parquet/Arrow, scikit-learn, NumPy, Pandas

### crdt-composition-algebra
- **Mô tả:** Go composition CRDT đại số + convergence proof + Interval Tree Clock
- **Tools:** Go, Python (test harness), WebSocket/SSE

### crdt-data-quality
- **Mô tả:** Coordinator-free DQ — 50 worker dùng CRDT (G-Counter/PNCounter/OR-Set/HLL)
- **Tools:** Python

### credit-scoring-pipeline-vn
- **Mô tả:** Feature engineering credit scoring chuẩn CIC
- **Tools:** Python, WebSocket/SSE

### csv-schema-inference-toolkit
- **Mô tả:** Infer schema CSV (type, nullability, encoding)
- **Tools:** Python, Avro, WebSocket/SSE

### customer-lifetime-value-segmenter
- **Mô tả:** RFM + CLV segmentation cho VN marketplace
- **Tools:** Python

### data-catalog-lineage
- **Mô tả:** Data catalog tự host — auto-discover + tag PII + column-level lineage UI
- **Tools:** Python, SQLite, FastAPI, sqlglot, Cytoscape.js, WebSocket/SSE

### data-contract-platform
- **Mô tả:** Data contract Git-native, version + enforce schema/SLA/semantic
- **Tools:** Python, SQLite, Parquet/Arrow, Pandas, WebSocket/SSE

### data-pipeline-v2
- **Mô tả:** Mock API → Postgres → dbt → Superset, orchestrate Airflow
- **Tools:** Python, PostgreSQL, Airflow, dbt, Superset, FastAPI

### data_quality_monitor
- **Mô tả:** Event-driven stream validator — Great Expectations + Soda mỗi micro-batch + Redis gate
- **Tools:** Python, Kafka, PostgreSQL, Redis, Parquet/Arrow, FastAPI, Prometheus, Grafana, Great Expectations, Soda, NumPy, Pandas
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `grafana/grafana:11.2.0`, `postgres:16-alpine`, `prom/prometheus:v2.54.0`, `redis:7.2-alpine`, `provectuslabs/kafka-ui`

### dbt-model-lineage-graph
- **Mô tả:** Parse dbt SQL cho `{{ ref() }}` `{{ source() }}`, build lineage graph
- **Tools:** Python, dbt

### dbt-semantic-bi-gateway
- **Mô tả:** dbt Semantic Layer + BI Gateway phục vụ Tableau/Looker/PowerBI/Metabase qua MetricFlow
- **Tools:** Python, PostgreSQL, DuckDB, dbt, BigQuery, Snowflake

### deadletter-queue-toolkit
- **Mô tả:** DLQ safety net cho streaming pipeline
- **Tools:** Python

### dedup-with-bloom
- **Mô tả:** Streaming deduplicator dùng Bloom filter
- **Tools:** Python, WebSocket/SSE

### delta-vs-iceberg-vs-hudi
- **Mô tả:** 3 mini implementation các table format dominant + benchmark
- **Tools:** Python, Iceberg, Hudi, Delta Lake

### deterministic-replay-engine
- **Mô tả:** Replay deterministic event log phân tán + causal ordering + non-determinism UDF detect
- **Tools:** Python

### differential-privacy-budget-manager
- **Mô tả:** Query gateway track ε-budget per analyst/dataset + Laplace/Gaussian mechanism
- **Tools:** Python, TypeScript, SQLite, FastAPI, React, NumPy

### disaggregated-storage-engine
- **Mô tả:** Compute-storage disaggregated — buffer pool ngoài compute, RDMA + Markov prefetcher
- **Tools:** Python, WebSocket/SSE

### distributed-query-planner
- **Mô tả:** Federated optimizer push WHERE vào MongoDB/Parquet/Postgres + cost model calibrated
- **Tools:** Python, PostgreSQL, MongoDB, Parquet/Arrow, sqlglot

### distributed-saga-orchestrator
- **Mô tả:** Saga pattern cho long-running multi-step data pipeline + rollback
- **Tools:** Python, SQLite

### dwh-data-quality-toolkit
- **Mô tả:** Composable DQ checks pure Python cho VN data warehouse
- **Tools:** Python

### ekyc-document-pipeline
- **Mô tả:** eKYC parse CCCD/CMND VN
- **Tools:** Python

### electricity-meter-iot-pipeline
- **Mô tả:** EVN smart-meter telemetry cumulative
- **Tools:** Python

### end2end-pipeline
- **Mô tả:** Production containerized — Kafka + Connect + ClickHouse + FastAPI + Dagster + OTel + Terraform/AWS
- **Tools:** Python, Kafka, ClickHouse, MinIO/S3, Avro, FastAPI, Prometheus, Grafana, OpenTelemetry, Dagster, Terraform, AWS
- **Docker images:** `bitnami/kafka:3.7.1`, `clickhouse/clickhouse-server:24.8`, `confluentinc/cp-schema-registry:7.6.1`, `grafana/grafana:11.2.2`, `grafana/loki:3.2.0`, `grafana/promtail:3.2.0`, `grafana/tempo:2.6.0`, `minio/minio:RELEASE.2024-10-02T17-50-41Z`, `nginx:1.27-alpine`, `otel/opentelemetry-collector-contrib:0.110.0`, `prom/prometheus:v2.54.1`

### exactly-once-pipeline
- **Mô tả:** Outbox + idempotency + Saga giữa Kafka/Postgres/DW/Redis
- **Tools:** Python, Kafka, PostgreSQL, Redis
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `postgres:16-alpine`, `redis:7-alpine`

### fb-posts
- **Mô tả:** Facebook posts data project (README dùng tagline mẫu — cần verify nội dung thực tế)
- **Tools:** Python (suy đoán)

### feature-store
- **Mô tả:** Real-time dual-layer feature store — Kafka + Redis online + Parquet offline, <10ms p99
- **Tools:** Python, Kafka, Redis, Parquet/Arrow, FastAPI, Prometheus, NumPy, Pandas
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `redis:7.2-alpine`

### finnhub-pipeline
- **Mô tả:** Finnhub WebSocket → Kafka → PyFlink → TimescaleDB + WebSocket push → React/Recharts
- **Tools:** Python, Kafka, Flink, TimescaleDB, FastAPI, React, WebSocket/SSE
- **Docker images:** `apache/kafka:3.7.0`, `timescale/timescaledb-ha:pg16`

### flash-sale-event-pipeline
- **Mô tả:** Event-streaming pipeline cho Shopee VN flash-sale
- **Tools:** Python

### flexible-paxos
- **Mô tả:** Flexible Paxos + dynamic quorum reconfig (Howard, Malkhi, Spiegelman 2016)
- **Tools:** Python

### forecasting-pipeline-scheduler
- **Mô tả:** K8s scheduler model DAG ⇒ Jackson network + B&B
- **Tools:** Python, WebSocket/SSE

### fraud-detection-banking-vn
- **Mô tả:** Fraud detection real-time cho internet banking VN
- **Tools:** Python

### gh-pipeline
- **Mô tả:** GH Archive end-to-end — dlt + Kestra + BigQuery + dbt + Bruin + Spark + Kafka
- **Tools:** Python, Kafka, Spark, PostgreSQL, Kestra, Bruin, dlt, BigQuery, Terraform, dbt
- **Docker images:** `bitnami/kafka:3.7`, `bitnami/spark:3.5`, `kestra/kestra`, `postgres:16`, `provectuslabs/kafka-ui`

### healthcare-claims-processor
- **Mô tả:** BHYT claims processor (bảo hiểm y tế VN)
- **Tools:** Python

### hlc-metadata-store
- **Mô tả:** Hybrid Logical Clock multi-region metadata store (loại bỏ causal inversion)
- **Tools:** Python

### hyperloglog-cardinality
- **Mô tả:** HyperLogLog++ distinct-count estimation streaming
- **Tools:** Python

### hyperloglog-sketch
- **Mô tả:** HyperLogLog++ cardinality estimator
- **Tools:** Python

### idempotency-key-store
- **Mô tả:** At-most-once execution qua idempotency key + TTL
- **Tools:** Python

### incremental-file-watcher
- **Mô tả:** Watch S3/MinIO prefix, dedupe file đã xử lý
- **Tools:** Python, MinIO/S3

### inflation-crawler
- **Mô tả:** Inflation crawler local-first: Common Crawl + BLS CPI + dashboard (không AWS/EMR/Spark cluster)
- **Tools:** Python, Spark, DuckDB, MinIO/S3, Parquet/Arrow, FastAPI, Chart.js, Pandas, AWS

### intelligent-compaction-engine
- **Mô tả:** Service compaction + Z-order + partition prune cho Delta + Iceberg
- **Tools:** Python, SQLite, Iceberg, Delta Lake

### ivm-engine
- **Mô tả:** Incremental View Maintenance — differential dataflow Python (kiểu Materialize)
- **Tools:** Python

### ivm-nested-aggregates
- **Mô tả:** IVM cho window function + correlated subquery + nested aggregate
- **Tools:** Python

### jepsen-linearizability
- **Mô tả:** Jepsen-style chaos harness + Wing-Gong linearizability verifier
- **Tools:** Python

### kafka-s3-replay
- **Mô tả:** Disaster recovery + event replay 30-day window từ Kafka/S3
- **Tools:** Python, Kafka, MinIO/S3, Avro, LocalStack
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `localstack/localstack:3.3`

### kll-sketch
- **Mô tả:** KLL streaming quantile sketch (Karnin-Lang-Liberty 2016)
- **Tools:** Python

### lakehouse-migration
- **Mô tả:** Migrate legacy DW → Delta/Iceberg + time-travel + ACID + incremental ingest
- **Tools:** Python, Spark, MinIO/S3, Iceberg, Delta Lake, Parquet/Arrow, Airflow, Snowflake, Pandas, AWS

### lakehouse-stack
- **Mô tả:** Self-contained 17-lab bootcamp data engineering, local Docker
- **Tools:** Kafka, Spark, PostgreSQL, MinIO/S3, Airflow, Metabase, Trino, Hive Metastore, Debezium
- **Docker images:** `apache/hive:standalone-metastore-4.1.0`, `bitnamilegacy/spark:3.5`, `bootcamp/airflow:2.8.0-datahub`, `confluentinc/cp-kafka:7.5.0`, `confluentinc/cp-zookeeper:7.5.0`, `debezium/connect:2.4`, `metabase/metabase:v0.50.17`, `minio/minio`, `postgres:15`, `trinodb/trino:480`

### lambda-kappa-migration
- **Mô tả:** Showcase migrate Lambda → Kappa + correctness validation
- **Tools:** Python, Kafka, Parquet/Arrow, LocalStack, NumPy, Pandas, AWS
- **Docker images:** `bitnami/kafka:3.5`, `bitnami/zookeeper:3.8`, `localstack/localstack`

### late-arriving-data-buffer
- **Mô tả:** Streaming primitive buffer event late theo event-time
- **Tools:** Python

### learned-index-lsm
- **Mô tả:** RMI learned index thay B-tree/Bloom trong LSM + ADWIN/KS drift detect
- **Tools:** Python, NumPy

### learned-layout-optimizer
- **Mô tả:** Closed-loop agent retune physical layout theo workload
- **Tools:** Python, NumPy

### log-based-cdc-from-scratch
- **Mô tả:** Đọc protocol log Postgres/MySQL không qua Debezium hay driver
- **Tools:** Python, PostgreSQL, MySQL

### logistics-eta-tracker
- **Mô tả:** Shipment tracking cho Shopee/Lazada/Tiki context VN
- **Tools:** Python

### lsm-merge-iterator
- **Mô tả:** K-way merge sorted runs (compaction primitive)
- **Tools:** Python

### lsm-remote-compaction
- **Mô tả:** LSM tree + tiered remote compaction qua gRPC + quorum commit
- **Tools:** Python, gRPC

### lsm-ts
- **Mô tả:** LSM engine từ scratch cho time-series (memtable, WAL, SSTable, Bloom, leveled compaction)
- **Tools:** Python

### materialized-view-selector
- **Mô tả:** View selection NP-hard cho BigQuery/Snowflake — greedy + simulated annealing
- **Tools:** Python, SQLite, BigQuery, Snowflake

### medallion-lakehouse
- **Mô tả:** Azure Databricks lakehouse bronze/silver/gold — Delta Live Tables + Unity Catalog + Power BI DirectLake + Terraform + DAB + GitHub Actions
- **Tools:** Python (PySpark), Databricks, Delta Lake, Unity Catalog, Power BI, Terraform, Azure, dlt, GitHub Actions

### minio-iceberg-lakehouse
- **Mô tả:** Iceberg table format từ scratch trên MinIO
- **Tools:** Python, MinIO/S3, Iceberg

### mlops_data_layer
- **Mô tả:** MLOps data layer — feature engineering + training/serving skew + drift + retraining
- **Tools:** Python, Kafka, PostgreSQL, Redis, Parquet/Arrow, FastAPI, Prometheus, Grafana, scikit-learn, NumPy, Pandas
- **Docker images:** `confluentinc/cp-kafka:7.6.0`, `confluentinc/cp-zookeeper:7.6.0`, `grafana/grafana:11.2.0`, `postgres:16-alpine`, `prom/prometheus:v2.54.0`, `redis:7.2-alpine`

### mobile-app-event-pipeline
- **Mô tả:** Mobile attribution kiểu Adjust/Appsflyer cho VN
- **Tools:** Python

### multi-pipeline-backpressure-mesh
- **Mô tả:** External backpressure coordination cho Flink/Spark (không sửa job nội bộ)
- **Tools:** Python, Redis, WebSocket/SSE
- **Docker images:** `redis:7-alpine`

### multi-platform-price-tracker
- **Mô tả:** Track giá same-SKU trên Shopee/Lazada/Tiki
- **Tools:** Python

### multi-region-data-mesh
- **Mô tả:** Active-active multi-region data product + vector clock + CRDT/LWW
- **Tools:** Python, SQLite, FastAPI

### multi-source-collector
- **Mô tả:** Multi-source ingestion HTTP API + DB CDC + file
- **Tools:** Python

### multi-source-reconciliation-engine
- **Mô tả:** Reconciliation tài chính 4 nguồn + fuzzy matching + 15-min SLA
- **Tools:** Python, NumPy, Pandas

### multi-tenant-ingestion-platform
- **Mô tả:** Self-service ingestion platform single-process per team
- **Tools:** Python

### multi-tenant-platform
- **Mô tả:** Shared infra + isolated storage + per-tenant compute quota + Postgres RLS
- **Tools:** Python, PostgreSQL, Redis, MinIO/S3, FastAPI, Prometheus
- **Docker images:** `minio/minio`, `postgres:16-alpine`, `redis:7-alpine`

### napas-247-transaction-monitor
- **Mô tả:** Real-time anomaly monitor NAPAS 247 instant inter-bank
- **Tools:** Python

### out-of-order-stream-processor
- **Mô tả:** Stream processor handle event đến muộn + watermark động per-key + what-if simulator
- **Tools:** Python, Flink (concept), WebSocket/SSE

### parquet-vs-orc-vs-avro-lab
- **Mô tả:** 3 implementation analytical storage format + benchmark
- **Tools:** Python, Parquet/Arrow, Avro

### partitioner-toolkit
- **Mô tả:** Shard/partition assignment primitives
- **Tools:** Python

### partitioning-strategy-advisor
- **Mô tả:** Profile SQL log → recommend partition column + bucket
- **Tools:** Python

### physical-plan-compiler
- **Mô tả:** Cascades planner trên ops Spark/dbt/Flink/DuckDB + auto cross-engine conversion
- **Tools:** Python, Spark, sqlglot

### pipeline-rca
- **Mô tả:** Automated root-cause attribution Interrupted Time Series
- **Tools:** Python, NumPy, Pandas

### pipeline-topology-compiler
- **Mô tả:** DSL khai báo pipeline DAG → compile Spark/Flink/dbt + chứng minh equivalence
- **Tools:** Python, Flink, Spark, dbt

### postgres-vs-clickhouse-benchmark
- **Mô tả:** Cross-engine query benchmark — 10 TPC-H + 5 custom
- **Tools:** Python, PostgreSQL, SQLite, ClickHouse

### practical-data-engineering-2026
- **Mô tả:** Lakehouse hiện đại laptop-scale (cập nhật 2026)
- **Tools:** Python, SQLite, DuckDB, MinIO/S3, Iceberg, Parquet/Arrow, Dagster, dlt, Streamlit, Pandas, WebSocket/SSE
- **Docker images:** `minio/minio`, `minio/mc`

### privacy-budget-ledger
- **Mô tả:** Privacy budget ledger RDP + zCDP composition + planner reject/rewrite query
- **Tools:** Python, SQLite, FastAPI, NumPy

### probabilistic-watermarks
- **Mô tả:** Watermark protocol probabilistic — P(late|advanced) < 0.1% với learned per-key delay
- **Tools:** Python, NumPy

### provenance-semiring-engine
- **Mô tả:** Provenance token + semiring operations (Green-Karvounarakis-Tannen)
- **Tools:** Python

### query-compiler-llvm
- **Mô tả:** SQL → LLVM compiler runtime specialization + speculative JIT + hot-swap
- **Tools:** Python, LLVM, WebSocket/SSE

### query-cost-optimizer
- **Mô tả:** CLI phân tích history BigQuery/Snowflake → recommend cluster/partition + $ saving
- **Tools:** Python, BigQuery, Snowflake, Pandas, sqlglot

### query-federation-engine
- **Mô tả:** SQL federation Postgres + MongoDB + S3 Parquet + REST API trong 1 query
- **Tools:** Python, PostgreSQL, MongoDB, MinIO/S3, Parquet/Arrow, Pandas, sqlglot

### query-optimizer
- **Mô tả:** Cascades optimizer pure Python + join reordering + cardinality + 10-table star schema demo
- **Tools:** Python

### raft-metadata-store
- **Mô tả:** Raft consensus from scratch + KV metadata store data catalog
- **Tools:** Python

### rate-limiter-toolkit
- **Mô tả:** Bộ rate limiter implementations
- **Tools:** Python

### reservoir-sampling
- **Mô tả:** Reservoir sampling toolkit pure Python
- **Tools:** Python

### retention-policy-engine
- **Mô tả:** Data retention TTL + count + size + composite rules
- **Tools:** Python

### reverse-etl
- **Mô tả:** Sync analytics → Slack/HubSpot/Salesforce/email theo schedule hoặc webhook
- **Tools:** Python, PostgreSQL, BigQuery, Snowflake, FastAPI

### review-sentiment-vietnamese
- **Mô tả:** Sentiment review tiếng Việt — SentimentClassifier protocol
- **Tools:** Python

### ride-share-trip-pipeline
- **Mô tả:** Grab/Gojek/Be-style ride-hailing trip pipeline VN
- **Tools:** Python

### savings-rate-engine
- **Mô tả:** Scrape + normalize lãi suất tiết kiệm NHTM VN
- **Tools:** Python, PostgreSQL, SQLite, FastAPI, Pandas

### sbv-circular-2345-compliance-pipeline
- **Mô tả:** Audit trail cho giao dịch chịu Quyết định 2345/QĐ-NHNN
- **Tools:** Python

### sbv-regulatory-reporting
- **Mô tả:** Báo cáo SBV tự động từ raw bank transaction + audit trail bất biến + reconciliation
- **Tools:** Python, Pandas

### schema-registry
- **Mô tả:** Schema registry 7-mode compatibility + auto-migration + transformation DSL + replay
- **Tools:** Python, SQLite, FastAPI

### schema-registry-evolution
- **Mô tả:** Schema evolution toolkit JSON/Avro/Protobuf streaming
- **Tools:** Python

### schema-registry-lite
- **Mô tả:** Schema registry in-memory + versioning + compatibility enforcement
- **Tools:** Python

### self-describing-data-warehouse
- **Mô tả:** DW mỗi table tự mô tả (lineage/quality/freshness/usage/incident)
- **Tools:** Python, PostgreSQL, SQLite, DuckDB, BigQuery

### self-healing-etl
- **Mô tả:** Prefect ETL — schema drift detect + healing + quarantine + alert
- **Tools:** Python, PostgreSQL, SQLite, Prefect, Pandas

### seller-performance-data-mart
- **Mô tả:** Star schema data mart cho marketplace VN (Shopee/Lazada/Tiki)
- **Tools:** Python

### serverless-autoscaler
- **Mô tả:** Predictive autoscaler Spark/Flink — ARIMA forecast + K8s HPA API
- **Tools:** Python, Kubernetes, Prometheus, NumPy, Pandas

### shopee-product-scraper-warehouse
- **Mô tả:** Pluggable scraper + in-memory warehouse e-commerce
- **Tools:** Python

### shuffle-dp-engine
- **Mô tả:** Shuffle-model differential privacy + cryptographic mixer + Balle analyzer
- **Tools:** Python, NumPy

### slowly-changing-dimensions-toolkit
- **Mô tả:** Kimball SCD Type 1/2/3/4/6 appliers
- **Tools:** Python

### streamdigest
- **Mô tả:** Gmail → dlt → BigQuery → OpenAI → Slack digest (Kestra)
- **Tools:** Python, DuckDB, Prefect, dlt, OpenAI/Ollama
- **Docker images:** `ollama/ollama`, `streamdigest:local`

### streaming-feature-store
- **Mô tả:** Feature store batch+streaming dùng cùng compute logic + drift detect + retraining
- **Tools:** Python, Kafka, Redis, Parquet/Arrow, FastAPI, NumPy, Pandas
- **Docker images:** `confluentinc/cp-kafka:7.5.0`, `confluentinc/cp-zookeeper:7.5.0`, `redis:7.2-alpine`

### streaming-ingestion-replay-engine
- **Mô tả:** Kafka-style replay engine + append-only log + segment + offset/time-based replay
- **Tools:** Python

### stream-state-backend
- **Mô tả:** Persistent queryable state backend Flink-style — RocksDB + Memory + 5 primitives + async migration + TTL compaction
- **Tools:** Python, RocksDB, FastAPI

### systemic-risk-monitor
- **Mô tả:** Streaming interbank contagion-risk + Memgraph graph + cycle detection + D3 dashboard
- **Tools:** Python, Memgraph, FastAPI, NumPy, Pandas, WebSocket/SSE, D3
- **Docker images:** `memgraph/memgraph-platform`

### t-digest
- **Mô tả:** t-digest (Dunning & Ertl 2014) pure Python
- **Tools:** Python

### telecom-cdr-pipeline
- **Mô tả:** VN telecom CDR pipeline end-to-end
- **Tools:** Python

### temporal-join-engine
- **Mô tả:** AS OF temporal join giữa 2 stream out-of-order + interval tree per-key + late correction
- **Tools:** Python, WebSocket/SSE

### tiered-storage-orchestrator
- **Mô tả:** Lifecycle hot/warm/cold (Redis/Postgres → Parquet/S3 → gzip)
- **Tools:** Python, PostgreSQL, Redis, MinIO/S3, Parquet/Arrow, LocalStack
- **Docker images:** `localstack/localstack:3`, `postgres:16-alpine`, `redis:7-alpine`

### timely-dataflow-engine
- **Mô tả:** Naiad timestamp `(epoch, iter)` cho batch/stream/iterative unified
- **Tools:** Python, WebSocket/SSE

### time-window-aggregator
- **Mô tả:** 3 window strategy chuẩn streaming pure Python
- **Tools:** Python

### tla-verified-pipeline
- **Mô tả:** TLA+ spec CDC → Kafka → DW → reverse-ETL + runtime monitor
- **Tools:** Python, Kafka, Flink, PostgreSQL, TLA+

### triage-pipeline
- **Mô tả:** Gmail → dlt → BigQuery → OpenAI → Slack (Kestra)
- **Tools:** Python, DuckDB, Kestra, dlt, BigQuery, FastAPI, WebSocket/SSE, OpenAI

### twitter_data-lakehouse_minio_drill_superset
- **Mô tả:** Lakehouse phân tích tweets Elon Musk — MinIO + Airflow + Apache Drill + Superset
- **Tools:** MinIO/S3, Airflow, Apache Drill, Superset, Docker

### vectorized-query-engine
- **Mô tả:** Vectorized columnar engine Python + Apache Arrow + predicate pushdown + late materialization
- **Tools:** Python, DuckDB, Parquet/Arrow, NumPy, sqlglot

### vietcombank-bidv-techcombank-fx-rate-aggregator
- **Mô tả:** Aggregate tỷ giá top-10 NHTM VN
- **Tools:** Python

### vn-address-parser
- **Mô tả:** Parse địa chỉ VN 3-cấp hành chính
- **Tools:** Python, WebSocket/SSE

### vn-banking-transaction-pipeline
- **Mô tả:** 18-bank commercial banking pipeline
- **Tools:** Python

### vn-business-day-calendar
- **Mô tả:** Lịch ngày làm việc + lễ tết VN
- **Tools:** Python, WebSocket/SSE

### vn-coffee-export-pipeline
- **Mô tả:** Giá xuất khẩu cà phê Robusta/Arabica
- **Tools:** Python

### vn-customs-declaration-pipeline
- **Mô tả:** Normalize tờ khai hải quan + tính thuế
- **Tools:** Python, WebSocket/SSE

### vn-ecommerce-order-pipeline
- **Mô tả:** Normalisation đơn hàng e-commerce VN
- **Tools:** Python, WebSocket/SSE

### vn-fishery-export-pipeline
- **Mô tả:** Xuất khẩu thủy sản + FOB pricing
- **Tools:** Python

### vn-insurance-claim-pipeline
- **Mô tả:** BHYT health insurance claim normaliser + payout
- **Tools:** Python

### vnpay-momo-zalopay-reconciliation
- **Mô tả:** Đối soát giao dịch VNPay/MoMo/ZaloPay
- **Tools:** Python

### vn-payroll-pipeline
- **Mô tả:** TNCN 7-bracket progressive
- **Tools:** Python

### vn-petroleum-pricing
- **Mô tả:** Tính giá xăng dầu theo Nghị định 95/2021/NĐ-CP
- **Tools:** Python

### vnpost-tracking-event-pipeline
- **Mô tả:** 5 hãng chuyển phát VN (Viettel Post, GHN, GHTK, JTV, BEST)
- **Tools:** Python

### vn-property-listing-normalizer
- **Mô tả:** Parse tin BĐS free-text VN thành structured
- **Tools:** Python, WebSocket/SSE

### vn-rice-supply-chain
- **Mô tả:** Chuỗi cung ứng lúa gạo + milling yield
- **Tools:** Python

### vn-ride-hailing-trip-pipeline
- **Mô tả:** 4-operator ride-hailing
- **Tools:** Python

### vn-school-grade-pipeline
- **Mô tả:** Classifier điểm THCS theo Thông tư 22/2021 MOET
- **Tools:** Python

### vn-shipping-pipeline
- **Mô tả:** Phí ship nội địa VN
- **Tools:** Python

### vn-stock-market-tick-pipeline
- **Mô tả:** Tick-data 3 sàn VN (HOSE, HNX, UPCOM)
- **Tools:** Python

### vn-stock-ticker-pipeline
- **Mô tả:** 3-board exchange data
- **Tools:** Python

### vn-tax-invoice-validator
- **Mô tả:** Validator hóa đơn điện tử VN
- **Tools:** Python

### vn-telecom-billing-pipeline
- **Mô tả:** Telecom CDR billing pipeline
- **Tools:** Python

### vn-utility-meter-pipeline
- **Mô tả:** EVN electricity meter
- **Tools:** Python

### volcano-push-adaptive-engine
- **Mô tả:** Query engine khởi đầu Volcano pull-mode, profile cardinality, switch sang push-based hot path
- **Tools:** Python

### wcoj-engine
- **Mô tả:** Worst-Case Optimal Join — Leapfrog Triejoin + Generic Join + GYO cycle detection
- **Tools:** Python, NumPy, Pandas

### zero-downtime-pipeline-upgrades
- **Mô tả:** Shadow v2 song song v1 + so sánh output + shift traffic dần
- **Tools:** Python, PyTorch

---

## 5. Một số phát hiện chung

1. **Python thống lĩnh** (169/176 project, ~96%). Chỉ một vài project dùng Go (`crdt-composition-algebra`) hoặc có thành phần TypeScript / React frontend.
2. **Pattern "pure Python, single-process"** xuất hiện ở >100 project — đây là cách codebase học và demo các thuật toán, không phải production clone.
3. **Stack Kafka + Postgres + Redis + FastAPI + Docker Compose** là backbone phổ biến nhất cho các project streaming / event.
4. **Lakehouse / DW** thường kết hợp **MinIO + Iceberg/Delta + Spark + Airflow**, với 1 project Azure Databricks (`medallion-lakehouse`).
5. **dbt + dlt + BigQuery** xuất hiện cùng nhau ở nhóm modern data stack (`gh-pipeline`, `streamdigest`, `triage-pipeline`, `dbt-semantic-bi-gateway`).
6. **Project VN-specific** đa phần dùng *pure Python toolkit* với pytest — phù hợp pattern compliance/regulatory tooling thay vì pipeline phức tạp.
7. **Probabilistic data structures** (Bloom, HLL, Count-Min, KLL, t-digest, reservoir) đều là pure Python + NumPy + pytest.
8. **Confluent Kafka 7.5/7.6** là image phổ biến; nhiều project chuyển sang `bitnami/kafka 3.6/3.7` (KRaft, không ZooKeeper).
9. **LocalStack** dùng để mô phỏng AWS local (S3 / KMS) ở 4 project.
10. **OpenTelemetry + Prometheus + Grafana + Loki + Tempo** stack đầy đủ chỉ thấy ở `end2end-pipeline`.

---

## 6. Unresolved Questions

- 1 project (`fb-posts`) có README copy nội dung từ `exactly-once-pipeline` — chưa rõ scope thực sự.
- 2 project (`airflow_minio_twitter_data_pipeline`, `twitter_data-lakehouse_minio_drill_superset`) tagline bị TOC ghi đè — đã suy đoán nội dung từ tên thư mục.
- Một số project trong README chính nhưng không tìm thấy thư mục (vd `data-pipeline-v2` cần verify).
- Có 83/176 project không có trong README chính nhưng vẫn có code/test riêng — có muốn phân tách "official" vs "incubating" không?
