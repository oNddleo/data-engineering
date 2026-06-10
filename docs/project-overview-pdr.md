# Project Overview / Product Definition

> **Loại:** Internal Knowledge Base & Engineering Portfolio
> **Tên:** `data-engineering` (monorepo)
> **Vị trí:** `/home/vsf-longnd56-l/Documents/oNddleo/data-engineering/`
> **Owner:** quangmata2208 (sophie-nguyenthuthuy GitHub origin)
> **Cập nhật:** 2026-06-10

---

## 1. Mục đích (Why)

Codebase này là một bộ sưu tập có chủ đích **176 project data engineering độc lập** — mỗi project minh hoạ một concept, pattern, hoặc kỹ thuật cụ thể trong lĩnh vực dữ liệu hiện đại. Các project được dùng cho:

1. **Học tập theo chiều sâu** — cài đặt lại từ scratch các thuật toán, protocol, format (LSM, Bloom, Paxos, Raft, CRDT, HLL, Iceberg, Avro…)
2. **Tham chiếu nhanh khi thiết kế hệ thống** — mỗi domain có ít nhất một "reference implementation" để xem cách wiring component
3. **Demo end-to-end cho candidates / stakeholders** — mỗi project chạy được với `make install && make test && make demo`
4. **Bộ trợ lý cho thị trường Việt Nam** — 27+ project xử lý quy định, format, dữ liệu đặc thù VN (NAPAS, SBV, BHYT, TNCN, CCCD/CMND, e-invoice…)

---

## 2. Phạm vi (Scope)

### Trong phạm vi
- Pipeline xử lý dữ liệu (batch / streaming / ETL / reverse-ETL)
- Storage engine từ scratch (LSM, B^ε-tree, ART, columnar)
- Query engine + optimizer (Cascades, Volcano, vectorized, federated, WCOJ)
- Data quality + governance + privacy (DP, lineage, contract, schema registry)
- Distributed systems primitives (consensus, CRDT, vector clock, HLC)
- Probabilistic data structures
- Lakehouse architecture (Delta, Iceberg, Hudi)
- VN-specific compliance / regulatory pipelines

### Ngoài phạm vi
- Production deployment trên cloud thật (chỉ Docker Compose local hoặc Terraform mẫu)
- Frontend application (chỉ dashboard tối giản FastAPI + Chart.js / React)
- Mobile app
- Mass scale (đa số single-process, không cluster thật)

---

## 3. Đối tượng sử dụng (Users)

| User | Mục đích chính |
|---|---|
| Senior Data Engineer | Reference khi thiết kế pipeline phức tạp / debate trade-off |
| Junior Data Engineer | Đọc code thật để học pattern và run demo |
| Hiring Panel | Xem chiều rộng & chiều sâu kỹ thuật của owner |
| Researcher / Student | Học thuật toán & protocol qua implementation cụ thể |
| Vietnamese fintech / banking | Lấy template compliance (SBV, NAPAS, BHYT, TNCN…) |

---

## 4. Cấu trúc Knowledge Base

```
data-engineering/
├── README.md                  ← Catalog 93 project chọn lọc (Built + Research MVP)
├── docs/                      ← Documentation (Vietnamese)
│   ├── project-overview-pdr.md     ← Tài liệu này
│   ├── codebase-summary.md         ← Tổng quan + phân nhóm 176 project
│   └── tools-by-project.md         ← Bảng tool/stack chi tiết per project
└── <176 project>/             ← Mỗi project có README, runtime, test riêng
    ├── README.md (Stack section + Quick start)
    ├── pyproject.toml hoặc requirements.txt
    ├── docker-compose.yml (nếu cần infra)
    ├── Makefile (install / test / demo target)
    ├── src/ tests/ examples/
    └── ...
```

---

## 5. Số liệu & Chỉ số

| Chỉ số | Giá trị |
|---|---:|
| Tổng số project | 176 |
| Project Python (pyproject.toml) | 158 (90%) |
| Project có Docker Compose | 111 (63%) |
| Project có Makefile | 100 (57%) |
| Project có README | 175 (99%) |
| Project có test suite | ~135 (76%) — phát hiện qua pytest |
| Project được README chính ghi nhận "Built" | 78 |
| Project Research MVP | 15 |
| Project VN-specific | 27+ |
| Tổng số test pass (theo README) | 106 (chỉ Research MVP) |

---

## 6. Nguyên tắc Thiết kế (Design Principles)

1. **Self-contained:** Mỗi project độc lập, runtime riêng (không shared library giữa các project).
2. **Reproducible:** `make install && make test && make demo` luôn chạy được.
3. **Pedagogical over production:** Code rõ ràng, thuật toán đúng, không cần scale tới petabyte.
4. **Vietnamese-aware:** Khi pipeline xử lý domain VN, dùng format / regulation / terminology VN chính xác.
5. **README làm contract:** Mỗi project README phải có Stack table + Quick start + Pipeline diagram.
6. **Test thật, không mock dataset:** Sample data tạo synthetic nhưng schema/business rule realistic.

---

## 7. Tech Stack tổng quan

### Core
- **Python 3.10+** (đa số project), packaging qua `pyproject.toml` + Hatch
- **Docker Compose** cho infra local (Kafka, Postgres, Redis, MinIO…)
- **Makefile** cho dev UX chuẩn

### Persistence
PostgreSQL · SQLite · DuckDB · Redis · ClickHouse · TimescaleDB · MongoDB · RocksDB · Memgraph · MinIO/S3

### Streaming / Messaging
Apache Kafka (Confluent + Bitnami) · Apache Flink · Apache Spark · Debezium

### Lakehouse
Apache Iceberg · Delta Lake · Apache Hudi · Apache Parquet · Apache Arrow · Apache Avro · Apache Drill · Trino · Hive Metastore

### Orchestration / Transformation
Airflow · Dagster · Prefect · Kestra · dbt · dlt · Bruin

### Quality / Governance
Great Expectations · Soda · Schema Registry · sqlglot

### Observability
Prometheus · Grafana · Loki · Tempo · OpenTelemetry

### API / UI
FastAPI · Streamlit · React + Recharts · D3 · Chart.js · WebSocket / SSE

### Cloud / IaC
LocalStack · Terraform · AWS · GCP (BigQuery) · Azure (Databricks) · Snowflake

### ML / Numeric
NumPy · Pandas · scikit-learn · PyTorch · MLflow · ARIMA

### Specialized
TLA+ · LLVM · gRPC

---

## 8. Mục tiêu Documentation

Tài liệu trong `docs/` hỗ trợ 3 use case chính:

1. **Onboarding 60 giây** → đọc `codebase-summary.md` để hiểu cấu trúc và chọn nhóm project quan tâm
2. **Tìm tool / stack** → đọc `tools-by-project.md` để xem nhanh project nào dùng Kafka / Spark / Iceberg / etc.
3. **Hiểu why** → đọc `project-overview-pdr.md` (file này)

> Mỗi project có README riêng — luôn đọc README của project cụ thể trước khi đi vào code.

---

## 9. Roadmap & Future Work (gợi ý)

- [ ] Thêm `docs/system-architecture.md` mô tả pattern chung (Lambda/Kappa/Medallion/Lakehouse)
- [ ] Thêm `docs/code-standards.md` chuẩn hoá Python style, naming, test naming
- [ ] Thêm `docs/deployment-guide.md` mô tả cách deploy 1 project lên cloud thật
- [ ] Thêm `docs/project-roadmap.md` theo dõi project nào đang in-progress / planned
- [ ] Tự động hoá doc sync từ README của project → docs/

---

## 10. Liên kết nội bộ

- [README chính](../README.md) — catalog 93 project chọn lọc
- [Codebase summary](./codebase-summary.md) — phân nhóm 176 project
- [Tools by project](./tools-by-project.md) — bảng tool/stack chi tiết

## 11. Unresolved Questions

- Owner mong muốn coverage tự động (số test pass) cho cả 176 project — hay chỉ 15 Research MVP như hiện tại?
- Có chuẩn hoá README template chung cho mỗi project không?
- Project trùng concept (`schema-registry` vs `schema-registry-lite` vs `schema-registry-evolution`; `hyperloglog-cardinality` vs `hyperloglog-sketch`) — giữ riêng hay merge?
