# Hướng dẫn chạy & triển khai

> Mọi lệnh chạy từ thư mục `sample-poc/`. Stack được điều khiển qua `make` (xem `make help`).

## Yêu cầu

- Docker + Docker Compose (daemon đang chạy).
- Cấu hình môi trường: copy `.env.example` → `.env` và chỉnh sửa.
  **Không commit `.env` thật.** Sinh secret thật:
  - `openssl rand -base64 32` (khóa mã hóa Lakekeeper)
  - `openssl rand -hex 32` (Superset secret)
  - Fernet (Airflow): `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`

## Khởi chạy nhanh — MVP (chỉ hạ tầng + ELT)

```bash
make up                 # dựng hạ tầng lõi: MinIO, Lakekeeper, Trino, Postgres
make seed               # tạo dữ liệu e-commerce tổng hợp vào source Postgres
make pipe-deps          # đảm bảo các phụ thuộc của container pipeline sẵn sàng
make ingest-bronze-full # Polars đọc -> PyIceberg ghi bronze (toàn bộ dòng)
make transform-silver   # dedup latest-per-PK
make transform-gold     # dựng marts gold
```

Hoặc chạy cả chuỗi ELT một lệnh:

```bash
make pipeline           # ingest-bronze -> transform-silver -> transform-gold
```

## Chứng minh nạp tăng dần (incremental)

```bash
make seed-more          # thêm/cập nhật dữ liệu nguồn
make ingest-bronze      # chỉ append các dòng có updated_at > watermark
make transform-silver
make transform-gold
```

Lần ingest tăng dần chỉ append delta; watermark được lưu ở `_control/watermarks.json`
trên bucket `warehouse`.

## Chạy lát cắt đầy đủ (Airflow + Superset)

```bash
make up-full            # bật thêm Airflow + Superset (profile `full`)
```

| Giao diện | URL | Đăng nhập |
|-----------|-----|-----------|
| Airflow | http://localhost:8082 | admin / admin |
| Superset | http://localhost:8088 | admin / admin |
| Trino | http://localhost:8080 | — |
| MinIO API | http://localhost:9000 | theo `.env` |

Trong Airflow, kích hoạt DAG `lakehouse_elt` (lịch `@hourly`). Đặt tham số `full_reload=true`
để nạp lại toàn bộ thay vì tăng dần.

## Các lệnh Makefile chính

| Lệnh | Tác dụng |
|------|----------|
| `make help` | Liệt kê tất cả target |
| `make up` / `make up-full` | Dựng hạ tầng lõi / kèm Airflow+Superset |
| `make seed` / `make seed-more` | Tạo / bổ sung dữ liệu nguồn tổng hợp |
| `make ingest-bronze` | Trích xuất delta -> bronze (append, tăng dần) |
| `make ingest-bronze-full` | Reset bronze và nạp lại toàn bộ |
| `make transform-silver` | Bronze -> silver (dedup + làm sạch) |
| `make transform-gold` | Silver -> gold marts |
| `make pipeline` | Chạy cả chuỗi ELT |
| `make test` | Chạy test đơn vị transform trong image runner (không cần stack) |

## Kiểm thử

```bash
make test               # pytest tests/ trong image pipeline
```

Test tập trung vào các hàm transform thuần (Polars) ở `tests/test_transforms.py` — chạy
được mà không cần dựng cả stack. Có sẵn truy vấn kiểm chứng Trino ở
`bi/trino_validation_queries.sql` và `infra/trino/smoke_test.sql`.

## Xử lý sự cố (thường gặp)

- **Service không gọi được nhau:** dùng **service DNS** (`minio:9000`, `lakekeeper:8181`),
  **không** `localhost`. Đây là lỗi số một.
- **Trino không đọc được MinIO:** đảm bảo dùng **native S3 filesystem** (Trino ~440+), trỏ
  path-style; không trộn lẫn cấu hình legacy `hive.s3.*`/`fs.s3.*`.
- **Superset báo "Invalid login":** kiểm tra `bi/superset/superset_config.py` đọc đúng
  `SQLALCHEMY_DATABASE_URI` (chung Postgres metadata cho init + webserver), tránh rơi về SQLite tạm.
- **Append bronze vỡ ở lần chạy thứ 2:** delta được cast về schema bảng đã thiết lập để
  không lệch null-width / decimal-precision giữa các lần chạy (đã xử lý trong code).

## Dọn dẹp

```bash
make down               # dừng và gỡ container (xem Makefile cho tùy chọn xóa volume)
```

> Tham khảo thêm runbook demo chi tiết (tiếng Anh): `../demo-runbook.md`.
