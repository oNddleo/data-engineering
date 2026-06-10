# Tổng quan Codebase Data Engineering

> **Vị trí:** `/home/vsf-longnd56-l/Documents/oNddleo/data-engineering/`
> **Loại:** Monorepo tổng hợp các project data engineering độc lập
> **Quy mô:** **176 project** (mỗi project là một repo độc lập với README riêng)
> **Ngôn ngữ chính:** Python (158/176 project dùng `pyproject.toml`)
> **Phân phối triển khai:** 111/176 project có `docker-compose.yml`, 100/176 có `Makefile`
> **Ngày cập nhật:** 2026-06-10

---

## 1. Mục tiêu Monorepo

Đây là bộ sưu tập có chủ đích các project về data engineering: pipeline xử lý dữ liệu, storage engine, query engine, hệ thống quản trị dữ liệu, và các nguyên thủy của hệ phân tán. Mỗi thư mục con là một project độc lập, có README, runtime và bộ test riêng. Codebase được dùng cho mục đích:

- Học tập & nghiên cứu các kỹ thuật data engineering hiện đại
- Demo end-to-end các kiến trúc (Lambda/Kappa/Lakehouse/Medallion)
- Cài đặt lại từ scratch các thuật toán nền tảng (CRDT, Paxos, Raft, LSM, B^ε-tree…)
- Phụ trợ pipeline cho thị trường Việt Nam (ngân hàng, viễn thông, thương mại điện tử, fintech, IoT…)

---

## 2. Thống kê tổng quát

| Hạng mục | Số lượng |
|---|---:|
| Tổng số project | 176 |
| Project có `pyproject.toml` (Python) | 158 |
| Project có `docker-compose.yml` | 111 |
| Project có `Makefile` | 100 |
| Project có `requirements.txt` | 36 |
| Project có README | 175 |
| **Built (theo README cha)** | 78 |
| **Research MVP** | 15 |
| **Project Việt Nam-specific** | 27+ |
| **Probabilistic data structures** | 8 |

---

## 3. Phân nhóm Project theo Domain

Sử dụng phân loại mở rộng từ README cha (6 nhóm chính + 7 nhóm research MVP) cộng thêm các nhóm domain-specific.

### 3.1 Streaming & Real-time (~20 project)

Xử lý sự kiện thời gian thực, windowing, watermark, CDC streaming, exactly-once semantics.

| Project | Tóm tắt |
|---|---|
| `adaptive-microbatch-optimizer` | Streaming processor tự điều chỉnh micro-batch window (50ms–5s) bằng PID controller |
| `banking-anomaly-pipeline` | Phát hiện gian lận thẻ ngân hàng real-time trên Kafka + PySpark + Redis state + FastAPI/SSE dashboard |
| `bft-stream` | Byzantine fault-tolerant streaming: PBFT chỉ chạy cho watermark advancement (<3× overhead vs Raft) |
| `cdc-pipeline` | Pipeline CDC production: Postgres WAL → Debezium → Kafka → DW + Avro schema evolution + LSN reorder buffer |
| `cdc-debezium-postgres-kafka` | Toolkit type-safe Python cho path Postgres → Debezium → Kafka |
| `cep-engine` | Complex Event Processing in-process sub-millisecond, JIT-compiled NFA, shared-memory ring buffer |
| `chandy-lamport-snapshot` | Cài đặt thuật toán snapshot phân tán Chandy-Lamport (Flink checkpointing) + exactly-once |
| `change-data-capture` | CDC toolkit thuần Python (event model + idempotency) |
| `exactly-once-pipeline` | Outbox + idempotency keys + Saga coordinator giữa Kafka/Postgres/DW/Redis |
| `finnhub-pipeline` | Finnhub WebSocket → Kafka → PyFlink (5s tumbling) → TimescaleDB → React/Recharts |
| `flash-sale-event-pipeline` | Pipeline event streaming cho Shopee VN flash-sale traffic |
| `kafka-s3-replay` | Hệ thống disaster recovery, replay any 30-day window từ Kafka/S3 |
| `log-based-cdc-from-scratch` | Đọc protocol log của Postgres/MySQL không qua Debezium hay driver |
| `mobile-app-event-pipeline` | Mobile attribution kiểu Adjust/Appsflyer cho thị trường VN |
| `multi-pipeline-backpressure-mesh` | Lớp điều phối backpressure ngoài cho Flink/Spark mà không sửa job nội bộ |
| `napas-247-transaction-monitor` | Monitor bất thường real-time cho hệ thống NAPAS 247 instant inter-bank |
| `out-of-order-stream-processor` | Stream processor xử lý event đến muộn với watermark động per-key, windowing, late-data policy |
| `streaming-feature-store` | Feature store đồng nhất code giữa batch và streaming, drift detection (KS/PSI/Chi2/JS) |
| `stream-state-backend` | State backend kiểu Flink (RocksDB + Memory), 5 state primitives, async migration |
| `streaming-ingestion-replay-engine` | Append-only log + segments, replay theo offset/time |
| `systemic-risk-monitor` | Monitor rủi ro tài chính liên ngân hàng — graph Memgraph + cycle detection + D3 dashboard |
| `temporal-join-engine` | AS OF temporal join giữa 2 stream out-of-order với interval-tree per-key |
| `vnpost-tracking-event-pipeline` | Pipeline event tracking 5 hãng chuyển phát VN (Viettel Post, GHN, GHTK…) |

### 3.2 Batch, ETL & Orchestration (~18 project)

Pipeline batch, orchestration end-to-end, ETL truyền thống.

| Project | Tóm tắt |
|---|---|
| `airflow_minio_twitter_data_pipeline` | Pipeline twitter với Airflow + MinIO (S3-compat) |
| `backfill-orchestrator` | Orchestrator backfill theo time-partition |
| `bitcoinMonitor` | ETL gần real-time: CoinGecko → SQLite → FastAPI dashboard (MVP) |
| `data-pipeline-v2` | Mock API → Postgres → dbt → Superset, orchestrate bằng Airflow |
| `distributed-saga-orchestrator` | Saga pattern cho data pipeline nhiều bước với rollback compensate |
| `end2end-pipeline` | Kafka + Connect + ClickHouse + FastAPI + Dagster + OTel + Terraform/AWS |
| `gh-pipeline` | GH Archive end-to-end: dlt + Kestra + BigQuery + dbt + Bruin + Spark + Kafka |
| `inflation-crawler` | Crawl CPI VN từ GSO, DuckDB, FastAPI, Docker |
| `pipeline-rca` | Auto root-cause attribution cho pipeline failure (Interrupted Time Series) |
| `pipeline-topology-compiler` | DSL khai báo DAG, compile ra Spark/Flink/dbt với chứng minh tương đương |
| `reverse-etl` | Đồng bộ analytic results → Slack, HubSpot, Salesforce, email |
| `savings-rate-engine` | Scrape + normalize lãi suất tiết kiệm các ngân hàng VN |
| `sbv-regulatory-reporting` | Pipeline tự động tạo báo cáo NHNN-VN với audit trail không sửa được |
| `self-healing-etl` | Prefect ETL detect schema drift, healing, quarantine, alert |
| `serverless-autoscaler` | Predictive autoscaling Spark/Flink — ARIMA forecast + K8s HPA |
| `streamdigest` | Gmail → dlt → BigQuery → OpenAI → Slack digest (orchestrate Kestra) |
| `triage-pipeline` | Email triage pipeline trên cloud-native stack |
| `twitter_data-lakehouse_minio_drill_superset` | Lakehouse phân tích tweets Elon Musk — MinIO + Airflow + Apache Drill + Superset |
| `zero-downtime-pipeline-upgrades` | Shadow v2 song song v1, so sánh output, chuyển traffic dần |

### 3.3 Data Quality & Governance (~12 project)

Đảm bảo chất lượng dữ liệu, lineage, contract, privacy.

| Project | Tóm tắt |
|---|---|
| `bayesian-dq-scorer` | Bayesian DQ scorer — Beta posterior cho completeness/freshness/uniqueness |
| `column-encryption-pipeline` | Mã hoá cột PII với KMS per-customer keys, live rotation, crypto erasure (GDPR RTBF) |
| `crdt-data-quality` | CRDT G-Counter/PNCounter/OR-Set/HLL cho DQ phân tán không coordinator |
| `data-catalog-lineage` | Data catalog tự host, auto-discover, tag PII, column-level lineage (sqlglot + Cytoscape) |
| `data-contract-platform` | Data contract Git-native, version + enforce schema/SLA/semantic |
| `data_quality_monitor` | Stream validator: Great Expectations + Soda mỗi micro-batch, dashboard + Redis gate |
| `differential-privacy-budget-manager` | Query gateway theo dõi ε-budget per analyst/dataset, Laplace/Gaussian mechanism |
| `dwh-data-quality-toolkit` | Composable DQ checks cho VN data warehouse |
| `mlops_data_layer` | MLOps data layer: feature engineering + training/serving skew + drift + retraining |
| `privacy-budget-ledger` | RDP/zCDP composition theorem cho privacy budget, planner reject/rewrite query |
| `schema-registry` | Schema registry 7-mode compatibility + auto-migration + transformation DSL |
| `schema-registry-evolution` | Schema evolution toolkit cho JSON/Avro/Protobuf streaming |
| `schema-registry-lite` | Schema registry in-memory với versioning và compatibility |

### 3.4 Query & Storage Engines (~20 project)

Query optimizer, storage engine từ scratch, indexing, compression.

| Project | Tóm tắt |
|---|---|
| `cardinality-learned-optimizer` | Neo/Bao optimizer loop: TreeLSTM cardinality + Thompson sampling + JOB benchmark |
| `column-statistics-collector` | Single-pass column profiler (null/distinct/min/max…) |
| `columnar-compression-testbed` | Testbed FSST/ALP/Gorilla + adaptive per-column selector + schema evolution |
| `cow-mor-benchmark` | Benchmark CoW vs MoR storage strategy + auto recommend |
| `distributed-query-planner` | Federated optimizer push WHERE vào MongoDB/Parquet/Postgres + cost model calibrated |
| `ivm-engine` | Incremental View Maintenance — differential dataflow Python |
| `learned-index-lsm` | RMI learned index thay B-tree trong LSM + ADWIN/KS drift detect + fallback |
| `lsm-merge-iterator` | K-way merge của sorted runs (compaction primitive) |
| `lsm-remote-compaction` | LSM tree + tiered remote compaction qua gRPC + quorum commit |
| `lsm-ts` | LSM engine từ scratch cho time-series (memtable, WAL, SSTable, Bloom, leveled compaction) |
| `materialized-view-selector` | View selection (NP-hard) cho BigQuery/Snowflake — greedy + simulated annealing |
| `query-compiler-llvm` | SQL-to-LLVM compiler runtime specialization + speculative JIT + hot-swap |
| `query-cost-optimizer` | Phân tích history BigQuery/Snowflake, recommend clustering/partition, ước tính $ saving |
| `query-federation-engine` | SQL federation: Postgres + MongoDB + S3 Parquet + REST API trong 1 query |
| `query-optimizer` | Cascades cost-based optimizer + join reordering + 10-table star schema demo |
| `tiered-storage-orchestrator` | Lifecycle hot/warm/cold (Redis/Postgres → Parquet/S3 → gzip) + EMA tracking |
| `vectorized-query-engine` | Vectorized columnar engine Python + Apache Arrow + predicate pushdown |
| `volcano-push-adaptive-engine` | Khởi đầu Volcano pull-mode, profile cardinality, switch sang push-based hot path |
| `wcoj-engine` | Worst-Case Optimal Join: Leapfrog Triejoin + Generic Join + GYO cycle detection |
| `physical-plan-compiler` | Cascades planner trên ops Spark/dbt/Flink/DuckDB + cross-engine conversion |

### 3.5 Data Warehouse & Lakehouse (~10 project)

Kiến trúc DW/Lakehouse, medallion, Iceberg/Delta/Hudi.

| Project | Tóm tắt |
|---|---|
| `dbt-model-lineage-graph` | Parse dbt SQL cho `{{ ref() }}` `{{ source() }}`, build lineage graph |
| `dbt-semantic-bi-gateway` | dbt Semantic Layer + BI Gateway phục vụ Tableau/Looker/PowerBI/Metabase qua MetricFlow |
| `delta-vs-iceberg-vs-hudi` | 3 implementation mini của các table format + benchmark so sánh |
| `intelligent-compaction-engine` | Service compaction/Z-order/partition prune cho Delta + Iceberg |
| `lakehouse-migration` | Migrate legacy DW → Delta/Iceberg với time-travel + ACID + incremental ingest |
| `lakehouse-stack` | Self-contained 17-lab bootcamp data engineering, chạy local Docker |
| `medallion-lakehouse` | Azure Databricks lakehouse bronze/silver/gold + Delta Live Tables + Unity Catalog + Power BI DirectLake + Terraform + DAB + CI/CD |
| `minio-iceberg-lakehouse` | Iceberg table format từ scratch trên MinIO |
| `multi-tenant-platform` | Multi-tenant platform: shared infra + isolated storage + per-tenant quota + Postgres RLS |
| `practical-data-engineering-2026` | Lakehouse hiện đại laptop-scale, cập nhật tooling 2026 |
| `self-describing-data-warehouse` | DW mỗi table tự mô tả (lineage/quality/freshness/usage/incident) cùng dữ liệu |

### 3.6 Distributed Systems & Infrastructure (~12 project)

Consensus, CRDT, vector clock, formal method, chaos engineering.

| Project | Tóm tắt |
|---|---|
| `crdt-composition-algebra` | Go: composition CRDT đại số + convergence proof + ITC anti-entropy + multi-region |
| `deterministic-replay-engine` | Replay deterministic event log phân tán + causal order + UDF non-determinism detect |
| `feature-store` | Real-time feature store 2 lớp: Kafka + Redis (online) + Parquet (offline), <10ms p99 |
| `flexible-paxos` | Flexible Paxos + dynamic quorum reconfig + TLA+ + Elle linearizability verifier |
| `hlc-metadata-store` | Hybrid Logical Clock metadata store multi-region (loại bỏ causal inversion NTP) |
| `jepsen-linearizability` | Jepsen-style chaos harness: network partition + clock skew + crash + Wing-Gong analysis |
| `lambda-kappa-migration` | Showcase migrate Lambda → Kappa + correctness validation |
| `multi-region-data-mesh` | Active-active multi-region data mesh + vector clock + CRDT/LWW + replication dashboard |
| `multi-source-reconciliation-engine` | Reconciliation tài chính 4 nguồn + fuzzy match + discrepancy classification + 15-min SLA |
| `raft-metadata-store` | Raft from scratch + KV metadata store data catalog (kiểu etcd) + linearizability test |
| `multi-tenant-ingestion-platform` | Self-service ingestion platform single-process |

### 3.7 Probabilistic Data Structures & Sampling (~10 project)

Sketch và sampling thuật toán cho streaming.

| Project | Tóm tắt |
|---|---|
| `bloom-filter` | Bloom filter toolkit production-grade, pure Python |
| `count-min-sketch` | Count-Min Sketch ước lượng tần suất |
| `dedup-with-bloom` | Streaming deduplicator dựa Bloom filter |
| `hyperloglog-cardinality` | HyperLogLog++ cho distinct-count ở streaming scale |
| `hyperloglog-sketch` | HyperLogLog++ cardinality estimator |
| `kll-sketch` | KLL streaming quantile sketch (Karnin-Lang-Liberty 2016) |
| `reservoir-sampling` | Reservoir sampling toolkit production-grade |
| `t-digest` | t-digest (Dunning & Ertl 2014), pure Python |
| `aqp-coreset-engine` | Approximate Query Processing qua coreset + confidence interval |
| `shuffle-dp-engine` | Shuffle-model differential privacy + cryptographic mixer + Balle analyzer |

### 3.8 Việt Nam-specific Pipelines (~27 project)

Pipeline phục vụ thị trường Việt Nam — banking, telecom, e-commerce, fintech, IoT, government compliance.

#### 3.8.1 Banking / Fintech VN

| Project | Tóm tắt |
|---|---|
| `credit-scoring-pipeline-vn` | Feature engineering credit scoring chuẩn CIC |
| `ekyc-document-pipeline` | eKYC pipeline cho CCCD/CMND |
| `fraud-detection-banking-vn` | Fraud detection real-time cho internet banking VN |
| `healthcare-claims-processor` | BHYT claims processor (bảo hiểm y tế) |
| `napas-247-transaction-monitor` | Monitor bất thường NAPAS 247 |
| `sbv-circular-2345-compliance-pipeline` | Audit trail cho Quyết định 2345/QĐ-NHNN |
| `sbv-regulatory-reporting` | Báo cáo tự động NHNN |
| `vietcombank-bidv-techcombank-fx-rate-aggregator` | Aggregate tỷ giá top-10 NHTM |
| `vn-banking-transaction-pipeline` | Pipeline 18-bank commercial banking |
| `vn-payroll-pipeline` | TNCN 7-bracket progressive |
| `vn-tax-invoice-validator` | Validator hóa đơn điện tử |
| `vnpay-momo-zalopay-reconciliation` | Đối soát giao dịch VNPay/MoMo/ZaloPay hàng ngày |

#### 3.8.2 Logistics / E-commerce / Retail VN

| Project | Tóm tắt |
|---|---|
| `customer-lifetime-value-segmenter` | RFM + CLV cho VN marketplace |
| `flash-sale-event-pipeline` | Shopee VN flash-sale |
| `logistics-eta-tracker` | Shipment tracking cho Shopee/Lazada/Tiki |
| `mobile-app-event-pipeline` | Adjust/Appsflyer-style |
| `multi-platform-price-tracker` | Track giá cùng SKU trên Shopee/Lazada/Tiki |
| `ride-share-trip-pipeline` | Grab/Gojek/Be ride-hailing trip |
| `seller-performance-data-mart` | Star schema cho marketplace VN |
| `shopee-product-scraper-warehouse` | Scraper + warehouse e-commerce |
| `vn-ecommerce-order-pipeline` | Normalisation đơn hàng e-commerce |
| `vn-ride-hailing-trip-pipeline` | 4-operator ride-hailing |
| `vn-shipping-pipeline` | Tính phí ship nội địa |
| `vnpost-tracking-event-pipeline` | 5 hãng chuyển phát VN |
| `vn-property-listing-normalizer` | Normalize tin BĐS free-text |

#### 3.8.3 Government / Tax / Insurance / Compliance

| Project | Tóm tắt |
|---|---|
| `vn-customs-declaration-pipeline` | Normalize tờ khai hải quan + tính thuế |
| `vn-insurance-claim-pipeline` | BHYT health insurance claim normaliser |
| `vn-school-grade-pipeline` | Classifier điểm THCS theo Thông tư 22/2021 MOET |
| `vn-business-day-calendar` | Lịch ngày làm việc + lễ tết VN |

#### 3.8.4 Telecom / IoT / Utilities VN

| Project | Tóm tắt |
|---|---|
| `air-quality-iot-pipeline` | Monitor PM2.5/PM10/NO2/SO2/O3/CO |
| `electricity-meter-iot-pipeline` | EVN smart-meter telemetry |
| `telecom-cdr-pipeline` | Telecom CDR pipeline |
| `vn-stock-market-tick-pipeline` | Tick-data 3 sàn VN |
| `vn-stock-ticker-pipeline` | 3-board exchange data |
| `vn-telecom-billing-pipeline` | Telecom CDR billing |
| `vn-utility-meter-pipeline` | EVN electricity meter |

#### 3.8.5 Agriculture / Energy / Commodities VN

| Project | Tóm tắt |
|---|---|
| `vn-coffee-export-pipeline` | Giá xuất khẩu cà phê Robusta/Arabica |
| `vn-fishery-export-pipeline` | Xuất khẩu thủy sản + FOB pricing |
| `vn-petroleum-pricing` | Tính giá xăng dầu theo Nghị định 95/2021/NĐ-CP |
| `vn-rice-supply-chain` | Chuỗi cung ứng lúa gạo + milling yield |
| `inflation-crawler` | Crawl CPI VN từ GSO |
| `savings-rate-engine` | Lãi suất tiết kiệm các NHTM |

#### 3.8.6 NLP / Address VN

| Project | Tóm tắt |
|---|---|
| `review-sentiment-vietnamese` | Sentiment review tiếng Việt |
| `vn-address-parser` | Parse địa chỉ VN 3 cấp hành chính |
| `fb-posts` | Facebook posts data project |

### 3.9 Resilience / Rate Limiting / Toolkit (~10 project)

Pattern resilience cho data pipeline.

| Project | Tóm tắt |
|---|---|
| `api-pagination-handler` | Pagination framework REST API (4 strategy) |
| `api-rate-limit-orchestrator` | Distributed token-bucket rate limiter |
| `circuit-breaker-toolkit` | Circuit breaker Fowler/Nygaard |
| `deadletter-queue-toolkit` | DLQ safety net cho streaming |
| `idempotency-key-store` | At-most-once execution với TTL |
| `incremental-file-watcher` | Watch S3/MinIO prefix, dedupe processed |
| `multi-source-collector` | Multi-source ingestion (HTTP API…) |
| `rate-limiter-toolkit` | Bộ rate limiter implementations |
| `retention-policy-engine` | Data retention TTL + count + size + composite |
| `slowly-changing-dimensions-toolkit` | Kimball SCD Type 1/2/3/4/6 |
| `time-window-aggregator` | 3 window strategy chuẩn streaming |
| `partitioner-toolkit` | Shard/partition assignment primitives |
| `partitioning-strategy-advisor` | Profile SQL log → recommend partition + bucket |
| `csv-schema-inference-toolkit` | Infer schema CSV (type, null, encoding) |
| `column-statistics-collector` | Single-pass column profiler |

### 3.10 Research MVP (15 project) — Theoretical foundations

| Project | Mô tả |
|---|---|
| `provenance-semiring-engine` | Annotate tuple bằng provenance token + semiring (Green-Karvounarakis-Tannen) |
| `aqp-coreset-engine` | Coreset + confidence interval |
| `shuffle-dp-engine` | Shuffle-model DP + cryptographic mixer |
| `probabilistic-watermarks` | Watermark protocol P(late\|advanced) < 0.1% với learned per-key delay |
| `timely-dataflow-engine` | Naiad timestamp `(epoch, iter)` cho unified batch/stream/iterative |
| `causal-feature-store` | Per-entity vector clock cho causally consistent feature |
| `b-epsilon-tree` | Write-optimized B^ε-tree + online ε tuning theo R/W ratio |
| `art-mvcc-index` | Adaptive Radix Tree + MVCC epoch-based reclamation + lock-free split |
| `ivm-nested-aggregates` | IVM cho window function + correlated subquery + nested aggregate |
| `disaggregated-storage-engine` | Compute-storage disaggregated + RDMA buffer pool + Markov prefetcher |
| `tla-verified-pipeline` | TLA+ spec CDC→Kafka→DW→reverse-ETL + runtime monitor |
| `learned-layout-optimizer` | RL agent retune Z-order/Hilbert/sort theo workload |
| `forecasting-pipeline-scheduler` | K8s scheduler model DAG ⇒ Jackson network + B&B ≤16 + shadow vs Airflow |
| `physical-plan-compiler` | Cascades planner trên Spark/dbt/Flink/DuckDB + cross-engine conversion |
| `adversarial-chaos-engine` | Symbolic execution + property-based chaos sinh input violating invariant |

---

## 4. Bố cục thư mục

```
data-engineering/
├── README.md               ← README chính (mô tả 93 project được chọn)
├── docs/                   ← thư mục tài liệu này
│   ├── codebase-summary.md     ← tài liệu này (tổng quan + phân nhóm)
│   ├── tools-by-project.md     ← bảng tool/stack per project
│   ├── project-overview-pdr.md ← product overview
│   └── ...
├── <project-1>/            ← mỗi project có README, runtime, test riêng
│   ├── README.md
│   ├── pyproject.toml hoặc requirements.txt
│   ├── docker-compose.yml (nếu cần infra)
│   ├── Makefile (nếu có install/test/demo target)
│   ├── src/ tests/ examples/ ...
│   └── ...
├── <project-2>/
└── ...
```

---

## 5. Tham chiếu chéo

- Bảng chi tiết tool/stack mỗi project: [`tools-by-project.md`](./tools-by-project.md)
- Tổng quan PDR & motivation: [`project-overview-pdr.md`](./project-overview-pdr.md)
- README cha (93 project chọn lọc): [`../README.md`](../README.md)

---

## 6. Unresolved Questions

- 83/176 project không xuất hiện trong README cha. Có cần phân tách thành 2 lớp “core” vs “experimental” không?
- Một số project (`fb-posts`) có README copy từ project khác — cần verify mục đích thực sự?
- Project `airflow_minio_twitter_data_pipeline` và `twitter_data-lakehouse_minio_drill_superset` có nội dung trùng concept (Twitter + MinIO) — có thể merge?
