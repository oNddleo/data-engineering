<div align="center">

# 🛠️ Data Engineering — 100+ Production-Grade Projects

**One of the most comprehensive open-source data-engineering portfolios on GitHub.**
From-scratch implementations of the systems behind every modern data platform —
Kafka • Iceberg • Delta Lake • Hudi • Parquet • CDC • Vector Clocks • CRDTs • LSM Trees • Differential Privacy • Causal Consistency • Bayesian DQ.

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776ab?logo=python&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/sophie-nguyenthuthuy/data-engineering?style=social)](https://github.com/sophie-nguyenthuthuy/data-engineering/stargazers)
[![Forks](https://img.shields.io/github/forks/sophie-nguyenthuthuy/data-engineering?style=social)](https://github.com/sophie-nguyenthuthuy/data-engineering/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/sophie-nguyenthuthuy/data-engineering)](https://github.com/sophie-nguyenthuthuy/data-engineering/commits/main)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy --strict](https://img.shields.io/badge/types-mypy%20strict-blue.svg)](https://mypy.readthedocs.io/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

#### ⭐ **If this repo is useful, please [give it a star](../../stargazers)** — it's how I know what to build next.

</div>

---

> [!TIP]
> **TL;DR** — 100+ self-contained data-engineering projects. Real algorithms, **2 500+ passing tests**, `mypy --strict`, multi-stage Dockerfiles, GitHub Actions matrix on Python 3.10/3.11/3.12, MIT-licensed. Zero or minimal runtime dependencies. Browse the [directory](#directory) ↓.

A curated monorepo of data-engineering work — pipelines, storage engines, query engines, table formats, streaming, governance, and distributed-systems primitives. **Each subdirectory is an independent project** with its own README, tests, Docker image, and CI workflow.

## ✨ Why this repo

- 🧱 **Production-grade**, not toy examples. Every project ships with strict type-checking, ruff lint, hand-written tests, Docker images, and GHA CI.
- 🧬 **From-scratch implementations** of the algorithms that power Kafka / Iceberg / Delta / Hudi / Parquet / CDC / Postgres WAL — read the code, learn how they actually work.
- 🐍 **Zero or minimal runtime dependencies** — most projects use only the Python stdlib. The wire formats are real; the code is auditable.
- ⚡ **One-command local runs** — `cd <project> && pip install -e ".[dev]" && pytest` works for every project. No external Kafka / Postgres / cluster required.
- 📚 **Pedagogical clarity** — every module has a top-of-file docstring explaining the algorithm, the trade-off, and the failure modes.

## 🌟 Featured Projects

If you only look at five, look at these:

| Project | What it is |
|---|---|
| [**log-based-cdc-from-scratch**](./log-based-cdc-from-scratch/) | Hand-written **MySQL binlog v4 parser** + **Postgres pgoutput** decoder. No Debezium, no driver dependencies. Real wire format, real tests. |
| [**minio-iceberg-lakehouse**](./minio-iceberg-lakehouse/) | A complete **Apache Iceberg-style** table format from scratch: schemas with stable field ids, manifests, snapshots, atomic-CAS metadata commit, time travel, schema evolution. |
| [**delta-vs-iceberg-vs-hudi**](./delta-vs-iceberg-vs-hudi/) | Mini implementations of all three table formats sharing one CDC workload harness so you can **see** the trade-offs in commits / write-amp / read-files. |
| [**streaming-ingestion-replay-engine**](./streaming-ingestion-replay-engine/) | A **Kafka-style append-only log** with offset & timestamp seek, on-the-fly transforms, persistent offset store, time-travel replay. |
| [**multi-source-collector**](./multi-source-collector/) | Multi-source ingestion (HTTP / CSV / Excel / FTP / Google Sheets) with **manifest-based idempotency** and slug-normalised naming. |

## 🚀 Quick start

```bash
# Pick a project, install, run its tests, see the demo:
git clone https://github.com/sophie-nguyenthuthuy/data-engineering.git
cd data-engineering/log-based-cdc-from-scratch
pip install -e ".[dev]"
pytest -q
lcdcctl info
```

That same recipe works for every project in the monorepo. Each one has a `Makefile` with `install`, `dev`, `test`, `lint`, `type`, `docker` targets.

## 📊 Stats

- **159 self-contained projects** across ingestion, storage, processing, governance, and platform — 105 curated in the [directory](#directory) below, the rest in the active build series ([CHANGELOG](CHANGELOG.md)).
- **79 production-grade builds** + **21 research MVPs** in the curated directory.
- **2 500+ tests** (each project ships its own suite — see per-project README).
- **mypy `--strict`** clean on every project.
- **Python 3.10 / 3.11 / 3.12** CI matrix per project.

## 🤝 Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first issues:
- Add a new edge case to any project's test suite.
- Wire a project up to a real backend (Kafka / Postgres / S3) behind its existing injectable adapter.
- Add benchmarks comparing against pyarrow / fastavro / etc.

## 🔍 Keywords

<sub>data engineering • lakehouse • apache iceberg • delta lake • apache hudi • parquet • orc • avro • change data capture • CDC • Postgres WAL • MySQL binlog • pgoutput • Kafka • Kafka Streams • Flink • streaming • event sourcing • exactly-once • watermarks • feature store • differential privacy • DBT • Airflow • Dagster • Prefect • semantic layer • cube • metric store • B-epsilon tree • LSM tree • ART • MVCC • Raft • Paxos • CRDT • vector clocks • HLC • hybrid logical clocks • TLA+ • Jepsen • linearizability • causal consistency • property-based testing • Hypothesis • approximate query processing • coresets • KLL sketch • Bayesian data quality • shuffle DP • k-anonymity • data mesh • data contracts • OpenLineage • schema registry • Iceberg time travel • Delta time travel • predicate pushdown • Z-order • Hilbert curve • Bloom filter • Cuckoo filter • IVM • differential dataflow • timely dataflow • Naiad • Volcano • Cascades query optimizer • cost-based optimizer • cardinality estimation • TPC-H • TPC-DS • MinIO • Trino • Presto • ClickHouse • DuckDB • Polars • Spark • Python 3.12 • mypy strict • ruff • from scratch • production-grade • monorepo</sub>

---

## Directory

**Built (79):**
- [Streaming & Real-time](#streaming--real-time) (15)
- [Batch, ETL & Orchestration](#batch-etl--orchestration) (18)
- [Data Quality & Governance](#data-quality--governance) (11)
- [Query & Storage Engines](#query--storage-engines) (17)
- [Data Warehouse & Lakehouse](#data-warehouse--lakehouse) (8)
- [Distributed Systems & Infrastructure](#distributed-systems--infrastructure) (10)

**Research MVPs (21):**
- [Query Processing & Compilation](#query-processing--compilation)
- [Distributed Systems Theory](#distributed-systems-theory)
- [Storage Engine Internals](#storage-engine-internals)
- [Streaming & Time](#streaming--time)
- [Data Correctness & Formal Methods](#data-correctness--formal-methods)
- [ML-Data System Co-design](#ml-data-system-co-design)
- [Platform & Meta-Systems](#platform--meta-systems)

---

### Streaming & Real-time

| Project | Description |
|---|---|
| [adaptive-microbatch-optimizer](./adaptive-microbatch-optimizer/) | Streaming processor with PID-controlled adaptive micro-batch windows (50ms–5s) |
| [banking-anomaly-pipeline](./banking-anomaly-pipeline/) | Real-time fraud detection on synthetic banking transactions — Kafka + PySpark Streaming, Redis state, FastAPI/SSE monitoring dashboard |
| [bft-stream](./bft-stream/) | Byzantine fault-tolerant stream processing: PBFT watermark consensus for windowed aggregations, benchmarked <3× overhead vs Raft |
| [cdc-pipeline](./cdc-pipeline/) | Production-grade CDC pipeline: Postgres WAL → Debezium → Kafka → data warehouse with Avro schema evolution and LSN-ordered reorder buffer |
| [cep-engine](./cep-engine/) | Sub-millisecond in-process Complex Event Processing engine — JIT-compiled NFA matchers, shared-memory ring buffer, no Kafka in the hot path |
| [chandy-lamport-snapshot](./chandy-lamport-snapshot/) | Chandy-Lamport distributed snapshot algorithm for streaming pipelines — consistent checkpoints, failure recovery, and exactly-once semantics proof |
| [exactly-once-pipeline](./exactly-once-pipeline/) | Exactly-once cross-system transaction pipeline: Outbox pattern + idempotency keys + Saga coordinator across Kafka, Postgres, warehouse, and Redis |
| [finnhub-pipeline](./finnhub-pipeline/) | Finnhub WebSocket → Kafka → PyFlink (5s tumbling aggregates) → TimescaleDB → React/Recharts dashboard |
| [kafka-s3-replay](./kafka-s3-replay/) | Disaster recovery & event replay system — replay any 30-day window of Kafka/S3 archived events into any downstream target |
| [multi-pipeline-backpressure-mesh](./multi-pipeline-backpressure-mesh/) | External backpressure coordination mesh for Flink/Spark streaming pipelines — no job internals modified |
| [out-of-order-stream-processor](./out-of-order-stream-processor/) | Out-of-order event-time stream processor with dynamic per-key watermarks, tumbling/sliding/session windows, late-data policies, and a what-if simulator |
| [stream-state-backend](./stream-state-backend/) | Flink-style persistent stream state backend: RocksDB + MemoryBackend, five state primitives, async topology migration, TTL compaction, FastAPI read API |
| [streaming-feature-store](./streaming-feature-store/) | Feature store where batch and streaming use identical compute logic, with nightly KS/PSI/Chi2/JS drift detection and automatic retraining trigger |
| [systemic-risk-monitor](./systemic-risk-monitor/) | Real-time interbank contagion risk detection — streaming graph (Memgraph), cycle detection, HHI concentration, cascade simulation, D3 dashboard |
| [temporal-join-engine](./temporal-join-engine/) | AS OF temporal joins for out-of-order event streams with per-key interval trees and late-arrival corrections |

### Batch, ETL & Orchestration

| Project | Description |
|---|---|
| [airflow_minio_twitter_data_pipeline](./airflow_minio_twitter_data_pipeline/) | Data pipeline using Airflow (orchestrator) and MinIO (S3-compatible object storage) |
| [bitcoinMonitor](./bitcoinMonitor/) | **MVP** — Near real-time ETL: CoinGecko → SQLite → FastAPI dashboard |
| [data-pipeline-v2](./data-pipeline-v2/) | Mock API → Postgres → dbt → Superset, orchestrated by Airflow |
| [distributed-saga-orchestrator](./distributed-saga-orchestrator/) | Saga pattern orchestrator for long-running, multi-step data pipelines with automatic compensation rollback |
| [end2end-pipeline](./end2end-pipeline/) | Production-grade containerized analytics pipeline: Kafka + Connect + ClickHouse + FastAPI + Dagster + OTel + Terraform/AWS |
| [gh-pipeline](./gh-pipeline/) | End-to-end GH Archive pipeline covering all 7 curriculum modules: dlt ingestion, Kestra orchestration, BigQuery warehouse, dbt analytics, Bruin platform, Spark batch, Kafka streaming |
| [inflation-crawler](./inflation-crawler/) | Vietnamese CPI and inflation data crawler — scrapes GSO sources, stores in DuckDB, serves via FastAPI, packaged in Docker |
| [pipeline-rca](./pipeline-rca/) | Automated root cause attribution for data pipeline failures using Interrupted Time Series causal impact analysis |
| [pipeline-topology-compiler](./pipeline-topology-compiler/) | DSL for declaring data pipelines as DAGs; compiles to Spark, Flink, or dbt with proof-of-equivalence checking |
| [reverse-etl](./reverse-etl/) | Reverse ETL: sync analytics results into Slack, HubSpot, Salesforce & email on a schedule or webhook trigger |
| [savings-rate-engine](./savings-rate-engine/) | Scheduled scraping + normalization pipeline for Vietnamese bank savings rates |
| [sbv-regulatory-reporting](./sbv-regulatory-reporting/) | Automated pipeline transforming raw bank transaction data into SBV regulatory report formats, with tamper-evident audit trail and reconciliation checks |
| [self-healing-etl](./self-healing-etl/) | Prefect ETL pipeline with schema drift detection, auto-healing, quarantine store, and structured alerts |
| [serverless-autoscaler](./serverless-autoscaler/) | Predictive warming control plane for Spark/Flink jobs — ARIMA forecasting + Kubernetes HPA API |
| [streamdigest](./streamdigest/) | Gmail → dlt → BigQuery → OpenAI → Slack digest pipeline (Kestra-orchestrated) |
| [triage-pipeline](./triage-pipeline/) | Email triage pipeline on a capable cloud-native stack |
| [twitter_data-lakehouse_minio_drill_superset](./twitter_data-lakehouse_minio_drill_superset/) | Data lakehouse for analysing Elon Musk tweets — MinIO + Airflow + Apache Drill + Superset |
| [zero-downtime-pipeline-upgrades](./zero-downtime-pipeline-upgrades/) | Shadow-mode v2 deployment alongside v1, with output diff comparison and gradual traffic shift |

### Data Quality & Governance

| Project | Description |
|---|---|
| [bayesian-dq-scorer](./bayesian-dq-scorer/) | Bayesian Data Quality Scorer: Beta posteriors for completeness, freshness, and uniqueness with uncertainty-aware anomaly alerts |
| [column-encryption-pipeline](./column-encryption-pipeline/) | Column-level PII encryption with per-customer KMS keys, live key rotation, and cryptographic erasure (RTBF) |
| [crdt-data-quality](./crdt-data-quality/) | CRDT-based distributed data quality counters — G-Counter, PNCounter, OR-Set, HyperLogLog. 50 pipeline workers, no coordinator, proven eventual consistency |
| [data-catalog-lineage](./data-catalog-lineage/) | Self-hosted data catalog: auto-discover assets, tag PII columns, visualize column-level lineage. FastAPI + sqlglot + Cytoscape.js |
| [data-contract-platform](./data-contract-platform/) | Automated data contract enforcement — schema + SLA + semantic validation, reliability scoring, breaking-change detection, CI enforcement |
| [data_quality_monitor](./data_quality_monitor/) | Event-driven stream validator: Great Expectations + Soda checks on every micro-batch, live quality dashboard, and Redis-backed downstream job blocking |
| [differential-privacy-budget-manager](./differential-privacy-budget-manager/) | Query gateway with ε-budget tracking per analyst/dataset, Laplace & Gaussian mechanisms, and a data-owner UI. Built for banking/healthcare data |
| [lyapunov-retraining-controller](./lyapunov-retraining-controller/) | Retraining-as-control-system: V = KL(model‖reference) as a Lyapunov function, trigger+deadbeat control of the real/synthetic data ratio with a Foster–Lyapunov stability bound — beats fixed-cadence retraining on stability, cost, and shock recovery |
| [mlops_data_layer](./mlops_data_layer/) | End-to-end MLOps data layer: feature engineering pipelines, training/serving skew detection, statistical drift monitoring, and automated retraining triggers |
| [privacy-budget-ledger](./privacy-budget-ledger/) | Privacy Budget Ledger with RDP and zCDP composition theorems — tighter than basic ε-composition with a query planner that rejects/rewrites over-budget queries |
| [schema-registry](./schema-registry/) | Schema registry with 7-mode compatibility enforcement, auto-migration generation, declarative transformation DSL, and event replay engine |

### Query & Storage Engines

| Project | Description |
|---|---|
| [cardinality-learned-optimizer](./cardinality-learned-optimizer/) | Neo/Bao query optimizer loop: TreeLSTM cardinality estimation, adaptive recompilation at 100× q-error, Thompson-sampling plan selection, JOB benchmark |
| [columnar-compression-testbed](./columnar-compression-testbed/) | Columnar Compression Research Testbed: FSST, ALP, Gorilla encoding with adaptive per-column selector and schema evolution |
| [cow-mor-benchmark](./cow-mor-benchmark/) | Copy-on-Write vs Merge-on-Read benchmark engine with automatic strategy recommendation |
| [distributed-query-planner](./distributed-query-planner/) | Federated query optimizer with predicate pushdown across MongoDB, Parquet, and PostgreSQL — cost model calibrated by sampling |
| [ivm-engine](./ivm-engine/) | Incremental View Maintenance engine — differential dataflow in Python |
| [learned-index-lsm](./learned-index-lsm/) | RMI learned index structures replacing B-tree lookups in an LSM engine, with ADWIN/KS drift detection and automatic fallback |
| [lsm-remote-compaction](./lsm-remote-compaction/) | LSM Tree with tiered remote compaction over gRPC and quorum-based commit |
| [lsm-ts](./lsm-ts/) | LSM-tree time-series storage engine from scratch — memtable, WAL, SSTables, bloom filters, leveled compaction |
| [materialized-view-selector](./materialized-view-selector/) | Self-optimizing materialized view selector for BigQuery & Snowflake — greedy + simulated annealing with cost-model calibration |
| [query-compiler-llvm](./query-compiler-llvm/) | SQL-to-LLVM query compiler with runtime specialization, speculative JIT, and hot-swap — inspired by HyPer/Umbra |
| [query-cost-optimizer](./query-cost-optimizer/) | Analyses BigQuery/Snowflake query history and recommends clustering keys, partitioning strategies, and flags expensive SQL patterns with estimated savings |
| [query-federation-engine](./query-federation-engine/) | Lightweight SQL federation engine: query Postgres, MongoDB, S3 Parquet, and REST APIs with a single SQL statement |
| [query-optimizer](./query-optimizer/) | Cascades cost-based query optimizer with join reordering, cardinality estimation, and 10-table star schema demo |
| [tiered-storage-orchestrator](./tiered-storage-orchestrator/) | Intelligent data lifecycle: hot (Redis/Postgres) → warm (Parquet/S3) → cold (gzip archive) with EMA access tracking, transparent read routing, rehydration SLA |
| [vectorized-query-engine](./vectorized-query-engine/) | Vectorized columnar query engine in Python with Apache Arrow, predicate pushdown, late materialization, and volcano/pipeline execution models |
| [volcano-push-adaptive-engine](./volcano-push-adaptive-engine/) | Query engine that starts in Volcano (pull) mode, profiles cardinality mid-query, and switches hot paths to push-based pipelines |
| [wcoj-engine](./wcoj-engine/) | Worst-Case Optimal Join Engine: Leapfrog Triejoin, Generic Join, and cyclic query planner with GYO hypergraph acyclicity detection |

### Data Warehouse & Lakehouse

| Project | Description |
|---|---|
| [dbt-semantic-bi-gateway](./dbt-semantic-bi-gateway/) | dbt Semantic Layer + BI Gateway — single source of truth serving Tableau, Looker, Power BI, Metabase via MetricFlow |
| [intelligent-compaction-engine](./intelligent-compaction-engine/) | Background service for intelligent compaction, Z-ordering, and partition pruning for Delta Lake and Iceberg tables |
| [lakehouse-migration](./lakehouse-migration/) | Migrate a legacy data warehouse to Delta Lake / Apache Iceberg with time-travel, ACID transactions, and incremental ingestion |
| [lakehouse-stack](./lakehouse-stack/) | Self-contained 17-lab data engineering bootcamp environment — everything runs locally in Docker |
| [medallion-lakehouse](./medallion-lakehouse/) | Production-grade Azure Databricks lakehouse: bronze/silver/gold on Delta Live Tables, Unity Catalog, Power BI DirectLake, Terraform + Databricks Asset Bundles |
| [multi-tenant-platform](./multi-tenant-platform/) | Multi-tenant data platform: shared infra with isolated storage, compute quotas, and PostgreSQL row-level security |
| [practical-data-engineering-2026](./practical-data-engineering-2026/) | Modern laptop-scale lakehouse — end-to-end data engineering project updated for 2026 tooling |
| [self-describing-data-warehouse](./self-describing-data-warehouse/) | A data warehouse where every table describes itself — lineage, quality, freshness, usage, and incidents queryable alongside the data |

### Distributed Systems & Infrastructure

| Project | Description |
|---|---|
| [crdt-composition-algebra](./crdt-composition-algebra/) | Algebraic CRDT composition with convergence proofs, delta-state sync, ITC anti-entropy, and multi-region partition validation |
| [deterministic-replay-engine](./deterministic-replay-engine/) | Deterministic replay of distributed event logs with causal ordering and UDF non-determinism detection |
| [feature-store](./feature-store/) | Real-time dual-layer feature store: Kafka + Redis + Parquet, <10ms serving latency for ML models |
| [flexible-paxos](./flexible-paxos/) | Flexible Paxos with dynamic quorum reconfiguration, TLA+ formal model, and Elle-style linearizability verifier |
| [hlc-metadata-store](./hlc-metadata-store/) | Multi-region metadata store using Hybrid Logical Clocks — eliminates causal inversions and stale reads that NTP-synced systems can't prevent |
| [jepsen-linearizability](./jepsen-linearizability/) | Jepsen-style chaos harness: injects network partitions, clock skew & process crashes into a streaming pipeline, then verifies linearizability via Wing-Gong history analysis |
| [lambda-kappa-migration](./lambda-kappa-migration/) | Data engineering showcase: migrating from Lambda to Kappa architecture with correctness validation |
| [multi-region-data-mesh](./multi-region-data-mesh/) | Active-active multi-region data mesh with vector clocks, CRDT/LWW/business-rule conflict resolution, and live replication dashboard |
| [multi-source-reconciliation-engine](./multi-source-reconciliation-engine/) | Financial reconciliation pipeline: 4-source fuzzy matching, discrepancy classification, confidence scoring, 15-min SLA |
| [raft-metadata-store](./raft-metadata-store/) | Raft consensus from scratch + distributed KV metadata store for a data catalog — leader election, log replication, snapshotting, membership changes, linearizability tests |

---

## Research MVPs

Working implementations of 15 research-grade project ideas. Each has:
- **Core algorithm** in `src/` (3–6 modules, 200–1000 LOC of Python)
- **Passing test suite** (5–9 tests per project, all green)
- **Runnable demo** in `examples/` showing the system in action
- **Makefile** with `install`, `test`, `demo` targets

Aggregate: **106 tests pass** across the 15 MVPs.

| Project | Tests |
|---|---|
| provenance-semiring-engine | 9/9 |
| aqp-coreset-engine | 6/6 |
| shuffle-dp-engine | 7/7 |
| probabilistic-watermarks | 6/6 |
| timely-dataflow-engine | 7/7 |
| causal-feature-store | 6/6 |
| b-epsilon-tree | 8/8 |
| art-mvcc-index | 9/9 |
| ivm-nested-aggregates | 8/8 |
| disaggregated-storage-engine | 7/7 |
| tla-verified-pipeline | 6/6 |
| learned-layout-optimizer | 7/7 |
| forecasting-pipeline-scheduler | 7/7 |
| physical-plan-compiler | 8/8 |
| adversarial-chaos-engine | 5/5 |

Pedagogical (single-process Python) — not production clones of HyPer/Naiad/DuckDB. The core algorithms are real and tested.

### Query Processing & Compilation

| Project | Status | Description |
|---|---|---|
| [query-compiler-llvm](./query-compiler-llvm/) | **Built** | SQL-to-LLVM compiler with runtime specialization, speculative JIT, hot-swap (HyPer/Umbra-inspired) |
| [wcoj-engine](./wcoj-engine/) | **Built** | Leapfrog Triejoin + Generic Join with GYO cyclic-query detection |
| [cardinality-learned-optimizer](./cardinality-learned-optimizer/) | **Built** | Neo/Bao optimizer loop with TreeLSTM cardinality + Thompson sampling |

### Distributed Systems Theory

| Project | Status | Description |
|---|---|---|
| [flexible-paxos](./flexible-paxos/) | **Built** | Flexible Paxos with dynamic quorum reconfiguration + TLA+ proof |
| [crdt-composition-algebra](./crdt-composition-algebra/) | **Built** | Algebraic CRDT composition with convergence proofs + ITC anti-entropy |
| [bft-stream](./bft-stream/) | **Built** | PBFT watermark consensus for streaming, <3× overhead vs Raft |

### Storage Engine Internals

| Project | Status | Description |
|---|---|---|
| [disaggregated-storage-engine](./disaggregated-storage-engine/) | **MVP** | Remote buffer pool over RDMA with Markov prefetcher and page-level coherence |
| [art-mvcc-index](./art-mvcc-index/) | **MVP** | Adaptive Radix Tree with MVCC via epoch-based reclamation, lock-free split |
| [b-epsilon-tree](./b-epsilon-tree/) | **MVP** | Write-optimized B^ε-tree with online ε tuning based on read/write ratio |

### Streaming & Time

| Project | Status | Description |
|---|---|---|
| [probabilistic-watermarks](./probabilistic-watermarks/) | **MVP** | Watermark protocol with P(late \| advanced) < 0.1% via learned per-key delay models |
| [ivm-nested-aggregates](./ivm-nested-aggregates/) | **MVP** | IVM for window functions, correlated subqueries, nested aggregates; switches delta↔recompute |
| [timely-dataflow-engine](./timely-dataflow-engine/) | **MVP** | Naiad-style timestamps `(epoch, iter)` for unified batch/stream/iterative |

### Data Correctness & Formal Methods

| Project | Status | Description |
|---|---|---|
| [tla-verified-pipeline](./tla-verified-pipeline/) | **MVP** | TLA+ spec for CDC→Kafka→DW→reverse-ETL with runtime monitor using same state machine |
| [provenance-semiring-engine](./provenance-semiring-engine/) | **MVP** | Green-Karvounarakis-Tannen provenance with Why / How / TriCS semiring instances |
| [shuffle-dp-engine](./shuffle-dp-engine/) | **MVP** | Shuffle-model DP with cryptographic mixer and Balle et al.'s optimal analyzer |

### ML-Data System Co-design

| Project | Status | Description |
|---|---|---|
| [learned-layout-optimizer](./learned-layout-optimizer/) | **MVP** | RL agent that continuously reorganises data layout (Z-order / Hilbert / sort) by workload |
| [aqp-coreset-engine](./aqp-coreset-engine/) | **MVP** | Approximate query processing via coresets with confidence-interval results |
| [causal-feature-store](./causal-feature-store/) | **MVP** | Per-entity vector clocks; serving guarantees causally consistent feature vectors across hot/cold |

### Platform & Meta-Systems

| Project | Status | Description |
|---|---|---|
| [forecasting-pipeline-scheduler](./forecasting-pipeline-scheduler/) | **MVP** | K8s scheduler that models DAGs as Jackson networks; B&B on subgraphs ≤16; shadow-mode vs Airflow |
| [physical-plan-compiler](./physical-plan-compiler/) | **MVP** | Cascades planner over Spark/dbt/Flink/DuckDB physical ops with auto-inserted cross-engine conversions |
| [adversarial-chaos-engine](./adversarial-chaos-engine/) | **MVP** | Symbolic-execution + property-based chaos: generates targeted invariant-violating inputs |

---

## Layout

```
data-engineering/
├── README.md               ← this file
├── <project>/              ← each project is an independent repo with its own .git
│   ├── README.md
│   └── ...
└── ...
```

## Notes

- All cloned via `git clone --depth 1` (no full history). The originals on GitHub still hold full history.
- `bitcoinMonitor/` is a local MVP. Stack: CoinGecko poller → SQLite → FastAPI + Chart.js dashboard.
- **Research MVPs** are working implementations — `cd <project>/ && make install && make test && make demo`. Pedagogical (Python, single-process) not production (no actual LLVM JIT, RDMA, Kubernetes). The 6 "Built" entries cross-referenced in those sections link to the corresponding fuller implementations.
- Each project's runtime is self-contained — see its README for setup.
