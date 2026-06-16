# Tổng quan dự án (PDR)

## Dự án là gì

**sample-poc** là một **lát cắt dọc (vertical slice)** mỏng của kiến trúc dữ liệu doanh
nghiệp 7 tầng, dùng để **chứng minh khả thi (Proof of Concept)** rằng:

> Dữ liệu vận hành (OLTP) có thể đổ vào một **lakehouse Iceberg mở** trên object storage,
> được biến đổi bằng engine tăng tốc Rust (**Polars**), và được truy vấn + trực quan hóa
> qua một cổng truy vấn federated (**Trino + Superset**) — tái lập được trên laptop chỉ
> với `docker compose`.

Đây là một **POC, không phải nền tảng đầy đủ**. Governance, security, EDMS, API gateway,
CDC real-time và tầng warehouse được **cố ý** để ngoài phạm vi.

## Mục tiêu

1. **Chứng minh luồng dữ liệu đầu-cuối:** Postgres → bronze → silver → gold → truy vấn được.
2. **Lakehouse mở:** dữ liệu nằm trên Iceberg/MinIO, nhiều engine cùng đọc (Polars, Trino).
3. **Tăng dần (incremental):** chỉ nạp dữ liệu mới qua cơ chế watermark, không quét lại toàn bộ.
4. **Tái lập được:** một lệnh `docker compose` dựng được cả stack trên 1 máy.
5. **Tự động hóa:** Airflow điều phối toàn bộ chuỗi ELT theo lịch.

## Tiêu chí chấp nhận (acceptance)

- File Parquet xuất hiện trong MinIO (bucket `warehouse`).
- Snapshot Iceberg tăng lên sau mỗi lần ingest.
- Trino truy vấn trả về dữ liệu từ các bảng gold.
- Superset hiển thị được dashboard từ marts gold.
- Truy vấn đối soát (reconciliation) giữa gold và doanh thu theo dòng khớp nhau (canary).

> **Lưu ý trạng thái:** tính tới journal `2026-06-13`, code đã hoàn chỉnh và test đơn vị
> pass, nhưng **kiểm thử runtime trực tiếp chưa chạy** vì Docker daemon offline ở thời điểm
> đó. Các tiêu chí trên vẫn là **giả định cần xác minh** khi chạy thật.

## Phạm vi — ánh xạ với kiến trúc 7 tầng

| Tầng tham chiếu | Kiến trúc đầy đủ | POC này |
|-----------------|------------------|---------|
| L1 Nguồn | CRM/ERP, DB, file, EDMS | PostgreSQL (e-commerce tổng hợp) |
| L2 Tích hợp | Kong, Kafka, Debezium, Airbyte | **ELT snapshot theo watermark** (không Kafka) |
| L3 Lakehouse | Airflow, MinIO, Iceberg, Spark, Trino, ClickHouse | Airflow + MinIO + Iceberg + **Polars** + Trino |
| L4 Governance | OpenMetadata, Great Expectations | chỉ một truy vấn đối soát (smoke check) |
| L5 EDMS | Mayan, Tika, Unstructured | — (ngoài phạm vi) |
| L6 Security | Keycloak, OPA, Ranger | — (mở, chỉ dùng cho POC) |
| L7 Trình bày | Superset, Trino gateway | Superset + Trino |

## Quyết định cắt giảm có chủ đích (không cắt thầm)

- **Hoãn CDC:** dùng ELT snapshot tăng dần theo watermark thay cho Debezium + Kafka
  (tiết kiệm ~2GB RAM + 3 container). CDC là hướng mở rộng đã ghi nhận.
- **Không Spark:** Polars (Rust) đủ cho transform ở quy mô POC; Trino lo truy vấn.
- **Không ClickHouse:** Trino-trên-Iceberg đáp ứng nhu cầu truy vấn của POC.
- **Governance rút gọn** còn một truy vấn đối soát gold-vs-doanh-thu-dòng (canary).

## Đối tượng & ngữ cảnh

- Đây là **một dự án con độc lập** trong monorepo portfolio ở thư mục gốc. Mỗi dự án con
  có README, test, Docker image và CI riêng. Không sửa README portfolio ở thư mục gốc.
- Dự án được xây từ kế hoạch tại `../../plans/260613-1035-poc-rust-lakehouse-end-to-end/`.

## Tài liệu liên quan

- [cong-cu-su-dung.md](cong-cu-su-dung.md) — chi tiết từng công cụ.
- [kien-truc-he-thong.md](kien-truc-he-thong.md) — kiến trúc & luồng dữ liệu.
- [huong-dan-chay-va-trien-khai.md](huong-dan-chay-va-trien-khai.md) — cách chạy.
- `../poc-architecture.md`, `../demo-runbook.md` — bản tiếng Anh gốc.
