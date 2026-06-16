# Lộ trình dự án

## Các phase đã xây (theo Makefile & plan gốc)

| Phase | Nội dung | Trạng thái |
|-------|----------|-----------|
| 1 | Hạ tầng nền (MinIO, Lakekeeper, Trino, các Postgres, mạng Docker) | ✅ Code xong |
| 2 | Dữ liệu nguồn tổng hợp (schema + seeder Faker) | ✅ Code xong |
| 3 | Trích xuất tăng dần Postgres → Iceberg bronze (Polars + PyIceberg) | ✅ Code xong |
| 4 | Biến đổi bronze → silver → gold (hàm thuần Polars) | ✅ Code xong |
| 5 | Điều phối bằng Airflow (DAG `lakehouse_elt`) | ✅ Code xong |
| 6 | BI bằng Superset (driver Trino) | ✅ Code xong |
| 7 | Demo + đối soát chấp nhận (canary reconciliation) | ✅ Code xong |

## Trạng thái hiện tại

- **Code-complete, test đơn vị pass.**
- **Runtime end-to-end CHƯA xác minh** (tại journal `2026-06-13`, Docker daemon offline).
  Các tiêu chí chấp nhận (Parquet xuất hiện ở MinIO, snapshot Iceberg tăng, Trino trả về
  rows) vẫn là **giả định cần kiểm chứng** khi chạy thật.

## Việc cần làm tiếp (ngắn hạn)

1. **Xác minh runtime:** chạy `make up` → `make seed` → `make pipeline` với Docker bật và
   xác nhận từng tiêu chí chấp nhận.
2. **Chạy lát cắt đầy đủ:** `make up-full`, kích hoạt DAG Airflow, dựng dashboard Superset
   từ marts gold.
3. **Xác nhận truy vấn đối soát** (canary) khớp giữa gold và doanh thu theo dòng.

## Hướng mở rộng (đã ghi nhận, ngoài phạm vi POC)

- **CDC real-time:** thay ELT snapshot theo watermark bằng Debezium + Kafka (đường stretch).
- **Đường ghi Iceberg thuần Rust:** hiện ghi qua PyIceberg vì chưa có đường Rust production
  (2026); cân nhắc DuckDB như một thay thế (xem `../poc-architecture.md`).
- **Governance đầy đủ:** OpenMetadata / Great Expectations / Elementary cho chất lượng + lineage.
- **Warehouse OLAP riêng:** ClickHouse nếu nhu cầu truy vấn vượt khả năng Trino-trên-Iceberg.
- **Security:** Keycloak / OPA / Ranger cho xác thực & phân quyền.
- **Mở rộng quy mô transform:** Spark nếu vượt quy mô phù hợp của Polars.

## Tham chiếu

- Plan gốc: `../../plans/260613-1035-poc-rust-lakehouse-end-to-end/`
- Journal: `../journals/2026-06-13-sample-poc.md`
- Kiến trúc đầy đủ (7 tầng): `../../knowledge/architecture-layer-diagram.md`
