---
phase: 9
title: "Tests & Documentation"
status: pending
priority: P2
effort: "1d"
dependencies: [5, 6, 8]
---

# Phase 9: Tests & Documentation

## Overview

Hoàn thiện POC bằng test suite (unit + integration smoke), Great Expectations checkpoint cho data quality, và bộ docs: architecture, demo runbook, ánh xạ với 7-layer reference.

## Requirements

- **Functional**: `make test` chạy mọi unit test trong < 60s không cần docker.
- **Functional**: `make demo-hybrid` end-to-end sạch từ `make down-hybrid` đến dashboard có data ≤ 10 phút.
- **Doc**: ánh xạ rõ component POC ↔ tầng 1–7 trong `knowledge/architecture-layer-diagram.md`.

## Architecture

```
tests/
├── unit/
│   ├── test_unit_normalizer.py     # bảng map đơn vị → SI
│   ├── test_outlier_detection.py   # window 3σ logic
│   ├── test_media_extractors.py    # Pillow + ffprobe mock
│   ├── test_iot_schema_parse.py    # PERMISSIVE mode + DLQ branch
│   └── test_delta_merge_idempotency.py  # silver MERGE 2 lần = 1 lần
├── integration/
│   ├── test_smoke_streaming.py     # spin Kafka+Spark in pytest container, 100 event
│   └── test_smoke_batch.py         # bronze → silver → gold trên Delta tạm
└── conftest.py                     # spark fixture, ephemeral warehouse
docs/
├── poc-architecture.md             # sơ đồ + bảng so sánh sample-poc vs hybrid
├── demo-runbook.md                 # command từng bước, thời lượng dự kiến
├── 7-layer-mapping.md              # ánh xạ component ↔ tầng L1-L7
├── troubleshooting.md
└── decisions/
    ├── 001-delta-vs-iceberg.md
    ├── 002-oss-spark-vs-databricks.md
    ├── 003-no-ml-inference-in-poc.md
    └── 004-streaming-on-airflow-poc-accepted-tradeoff.md   <!-- Updated: Validation Session 1 — Q2 ADR -->

```

## Related Code Files

- Create: `tests/unit/*.py`, `tests/integration/*.py`, `tests/conftest.py`
- Create: `tests/requirements.txt` (pytest, pyspark, delta-spark, chispa, testcontainers-python, kafka-python)
- Create: `docs/*.md` (5 file chính)
- Create: `docs/diagrams/` (mermaid source export)
- Create: `quality/great_expectations/` (suite + checkpoint config)
- Update: `README.md` root sample-poc-hybrid

## Implementation Steps

1. **Unit tests**:
   - `chispa` so sánh DataFrame; spark fixture session-scoped với `delta-spark` extension.
   - Tách logic transform thành pure function (lib/) để test không cần I/O.
   - Mock ffprobe bằng monkeypatch trả về JSON tĩnh.
2. **Integration smoke**:
   - `testcontainers-python` spin Kafka + MinIO ephemeral.
   - Submit `streaming_iot_bronze.py` với `Trigger.AvailableNow` (xử lý 1 batch rồi exit) để test deterministic.
   - Assert delta count + thumbnail object exist.
3. **Great Expectations**:
   - Suite `iot_readings_silver`: `value_si between (-100, 1000)`, `device_id matches regex`, `quality_flag in {ok,outlier,missing_dim}`.
   - Suite `media_objects_bronze`: `thumbnail_key not null`, `size_bytes > 0`.
   - Checkpoint chạy ở DAG 3 (phase 7).
4. **Docs**:
   - `poc-architecture.md`: mermaid pipeline, bảng so sánh `sample-poc` (Polars/Iceberg) vs `sample-poc-hybrid` (Spark/Delta).
   - `demo-runbook.md`: timing từng `make` command.
   - `7-layer-mapping.md`: bảng L1..L7 ↔ component thực tế + cái gì out of scope.
   - 3 ADR (Architecture Decision Records) ngắn gọn.
5. **README.md** kiểu sample-poc cũ, kèm Quickstart MVP + Full + Pipeline đặc trưng IoT/Media.

## Success Criteria

- [ ] `make test` pass 100%, ≥ 25 test case.
- [ ] `make demo-hybrid` từ zero đến dashboard có data trong 10 phút trên laptop 16 GB.
- [ ] GE checkpoint chạy thành công, lưu HTML report.
- [ ] Docs cover đủ: kiến trúc, ánh xạ 7-layer, decisions, runbook, troubleshooting.
- [ ] README có badge "POC", link plan này, link sample-poc gốc.

## Risk Assessment

- **Testcontainers chậm trên CI**: gắn marker `slow`; cho phép skip ở local nếu thiếu docker.
- **Spark session leak giữa test**: dùng `module` scope + `spark.stop()` ở fixture teardown.
- **Docs out of sync khi code đổi**: thêm step ở `make demo-hybrid` đọc và in version tag từ docs để dev nhận diện.

## Next Steps (sau POC)

- Migrate spark-submit YAML sang **Databricks Asset Bundles** (mode hybrid `--two` đã loại bỏ vì user chọn OSS local).
- Thêm Unity Catalog OSS (Unity Catalog 0.2+) thay Hive Metastore cho governance đầy đủ hơn.
- Bổ sung ML inference (YOLO/Whisper) như plan riêng — đã out of scope tại POC này.
