# Các công cụ sử dụng trong dự án

Tài liệu này mô tả **từng công cụ** trong stack: nó là gì, đóng vai trò gì trong
dự án, **vì sao được chọn**, và cách nó được cấu hình / sử dụng tại đây.

## Bảng tổng quan stack

| Tầng (layer) | Công cụ | Viết bằng Rust? | Vai trò trong dự án |
|--------------|---------|:---------------:|---------------------|
| Nguồn (Source) | **PostgreSQL** | — | CSDL OLTP chứa dữ liệu e-commerce tổng hợp (Faker) |
| Object store | **MinIO** | — | Lưu trữ S3 cho file dữ liệu Iceberg (Parquet) |
| Định dạng bảng | **Apache Iceberg** | — | Table format mở: snapshot, time-travel, schema evolution |
| Catalog | **Lakekeeper** | ✅ | REST catalog quản lý metadata bảng Iceberg |
| Trích xuất / biến đổi | **Polars** | ✅ | Đọc Postgres + dedup/join/aggregate (engine Rust) |
| Ghi Iceberg | **PyIceberg** | Python | Đường ghi (write) vào bảng Iceberg |
| Truy vấn | **Trino** | JVM | Query engine federated trên Iceberg |
| BI / Dashboard | **Apache Superset** | Python | Trực quan hóa marts tầng gold |
| Điều phối | **Apache Airflow** | Python | Lập lịch & chạy chuỗi ELT bronze → silver → gold |
| Đóng gói | **Docker Compose** | — | Khởi chạy toàn bộ stack trên 1 máy |

> **Về "tăng tốc bằng Rust":** Rust là thành phần cốt lõi ở **catalog (Lakekeeper)**
> và **engine đọc/biến đổi (Polars)**. Đường **ghi** Iceberg đi qua **PyIceberg (Python)**
> vì tính đến 2026 chưa có đường ghi Iceberg thuần Rust mức production. Đây là khoảng
> trống đã được ghi nhận trung thực, không che giấu.

---

## 1. PostgreSQL — nguồn dữ liệu OLTP

- **Là gì:** CSDL quan hệ truyền thống.
- **Vai trò:** mô phỏng hệ thống vận hành (đơn hàng e-commerce). Dữ liệu tổng hợp
  được tạo bằng **Faker** (xem `source/seed_source_data.py`, schema ở `source/schema.sql`).
- **Bảng chính:** `customers`, `products`, `orders`, `order_items` — mỗi bảng có khóa
  chính (`id`) và cột mốc thời gian `updated_at` phục vụ trích xuất tăng dần.
- **Ghi chú:** cũng có một Postgres thứ hai (`meta-db`) làm CSDL metadata dùng chung
  cho Lakekeeper, Airflow và Superset (mỗi dịch vụ một database logic riêng).

## 2. MinIO — object storage (S3)

- **Là gì:** object store tương thích API S3, chạy on-premise / local.
- **Vai trò:** nơi lưu trữ vật lý mọi file dữ liệu + metadata của Iceberg (bucket `warehouse`).
- **Lý do chọn:** thay thế AWS S3 cho môi trường local, không cần cloud.
- **Cấu hình quan trọng:** dùng **path-style** (`http://minio:9000/bucket/key`) — bắt buộc
  cho MinIO; virtual-hosted (`http://bucket.minio:9000/...`) không phân giải được qua Docker DNS.

## 3. Apache Iceberg — định dạng bảng (table format)

- **Là gì:** table format mở cho lakehouse: hỗ trợ snapshot, ACID commit, time-travel,
  tiến hóa schema.
- **Vai trò:** chuẩn hóa cách dữ liệu được tổ chức trên MinIO theo 3 tầng medallion:
  `bronze` (thô, append-only), `silver` (đã làm sạch / dedup), `gold` (marts nghiệp vụ).
- **Lý do chọn:** chuẩn mở, không khóa nhà cung cấp; cho phép nhiều engine (Polars, Trino)
  cùng đọc một bảng.

## 4. Lakekeeper — Iceberg REST catalog (Rust ✅)

- **Là gì:** dịch vụ catalog REST cho Iceberg, viết bằng Rust.
- **Vai trò:** "sổ đăng ký" metadata — ánh xạ tên bảng (`bronze.customers`) tới vị trí
  file trên MinIO; quản lý snapshot và commit.
- **Cấu hình:** lưu metadata trên `meta-db` (Postgres); warehouse được đăng ký qua
  `infra/lakekeeper/bootstrap.sh`. Cả pipeline (PyIceberg) lẫn Trino đều trỏ tới
  endpoint `http://lakekeeper:8181/catalog`.

## 5. Polars — engine trích xuất & biến đổi (Rust ✅)

- **Là gì:** thư viện DataFrame hiệu năng cao, lõi viết bằng Rust.
- **Vai trò:**
  - **Đọc** dữ liệu từ Postgres qua `connectorx` (`pl.read_database_uri`).
  - **Biến đổi** silver/gold: dedup latest-per-PK, làm sạch, join, aggregate
    (xem `pipeline/transforms/silver.py`, `pipeline/transforms/gold.py`).
- **Lý do chọn:** nhanh, ít phụ thuộc, thay thế Spark ở quy mô POC (không cần JVM nặng).
- **Pattern:** các transform là **hàm thuần (pure functions)** trên `pl.DataFrame` →
  dễ test đơn vị (`tests/test_transforms.py`) mà không cần dựng cả stack.

## 6. PyIceberg — đường ghi Iceberg (Python)

- **Là gì:** thư viện Python để thao tác bảng Iceberg.
- **Vai trò:** **ghi** Arrow table vào Iceberg (`append` cho bronze, `overwrite` cho
  silver/gold) — xem `pipeline/io_iceberg.py`, `pipeline/iceberg_catalog.py`.
- **Lý do tồn tại:** chưa có đường ghi Iceberg thuần Rust mức production (2026), nên
  Polars/Rust lo đọc + transform, PyIceberg lo ghi. Đã cast schema mỗi delta về schema
  bảng để append tăng dần không vỡ vì lệch kiểu/độ rộng cột giữa các lần chạy.

## 7. Trino — query engine

- **Là gì:** engine SQL phân tán (federated), chạy trên JVM.
- **Vai trò:** truy vấn trực tiếp bảng Iceberg trên MinIO thông qua Lakekeeper catalog.
- **Cấu hình (`infra/trino/etc/catalog/iceberg.properties`):**
  - `connector.name=iceberg`, `iceberg.catalog.type=rest`
  - `iceberg.rest-catalog.uri=http://lakekeeper:8181/catalog`
  - Dùng **native S3 filesystem** (Trino ~440+) trỏ về MinIO. **Không** trộn lẫn với
    cấu hình legacy `hive.s3.*`/`fs.s3.*` (lỗi thường gặp).
- **Cổng:** `8080`.

## 8. Apache Superset — BI / dashboard (Python)

- **Là gì:** nền tảng BI mã nguồn mở.
- **Vai trò:** kết nối tới Trino (driver đã build sẵn trong image) để dựng biểu đồ /
  dashboard từ các marts tầng gold.
- **Cấu hình quan trọng (`bi/superset/superset_config.py`):** đọc `SQLALCHEMY_DATABASE_URI`
  từ biến môi trường để init container và webserver dùng **chung** CSDL metadata Postgres.
  Nếu không có file này, image gốc rơi về SQLite tạm → user admin "biến mất" ("Invalid login").
- **Cổng:** `8088` (admin/admin).

## 9. Apache Airflow — điều phối (Python)

- **Là gì:** nền tảng lập lịch & điều phối workflow.
- **Vai trò:** chạy DAG `lakehouse_elt` (`orchestration/dags/lakehouse_elt_dag.py`):
  `extract_load_bronze → transform_silver → transform_gold`, lịch `@hourly`.
- **Thiết kế:** các task chỉ **shell-out** sang chính các script pipeline (không nhân bản
  logic transform). `max_active_runs=1` để tránh tranh chấp ghi file watermark.
- **Executor:** LocalExecutor. **Cổng UI:** `8082` (vì `8080` đã dành cho Trino).

## 10. Docker Compose — đóng gói & chạy

- **Vai trò:** định nghĩa toàn bộ dịch vụ trên một mạng bridge `lakehouse`. Các service
  gọi nhau bằng **service DNS** (`minio:9000`, `lakekeeper:8181`) — không dùng `localhost`
  (đây là lỗi thường gặp nhất).
- **Profiles:** mặc định chạy hạ tầng lõi; `full` bật thêm Airflow + Superset; `pipeline`
  tự bật khi `docker compose run` script ELT.

---

## Khái niệm bổ trợ

- **Watermark (`pipeline/watermark.py`):** mốc thời gian `updated_at` lớn nhất đã nạp,
  lưu dạng một file JSON trên bucket warehouse (`_control/watermarks.json`). Mỗi lần chạy
  chỉ đọc các dòng mới hơn watermark rồi cập nhật lại — đây là cơ chế **incremental ELT**
  thay cho CDC (Debezium/Kafka) ở quy mô POC.
- **Medallion (bronze/silver/gold):** mô hình phân tầng dữ liệu — thô → sạch → sẵn dùng
  cho nghiệp vụ. Xem chi tiết ở [kien-truc-he-thong.md](kien-truc-he-thong.md).
