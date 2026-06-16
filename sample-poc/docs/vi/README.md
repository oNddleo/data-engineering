# Tài liệu (tiếng Việt) — sample-poc

Bộ tài liệu tiếng Việt cho dự án **sample-poc — Lakehouse đầu-cuối tăng tốc bằng Rust**
(Postgres → Polars → Iceberg/MinIO → Trino → Superset, điều phối bằng Airflow).

> Tài liệu tiếng Anh gốc nằm ở `../demo-runbook.md` và `../poc-architecture.md`.
> Bộ tiếng Việt này diễn giải lại đầy đủ và nhấn mạnh phần **công cụ sử dụng**.

## Mục lục

| Tài liệu | Nội dung |
|----------|----------|
| [tong-quan-du-an.md](tong-quan-du-an.md) | Tổng quan dự án, mục tiêu, phạm vi (PDR) |
| [cong-cu-su-dung.md](cong-cu-su-dung.md) | **Các công cụ dùng trong dự án** — vai trò, lý do chọn, cách dùng |
| [kien-truc-he-thong.md](kien-truc-he-thong.md) | Kiến trúc hệ thống, luồng dữ liệu, mạng Docker |
| [huong-dan-chay-va-trien-khai.md](huong-dan-chay-va-trien-khai.md) | Hướng dẫn cài đặt, chạy, demo, xử lý sự cố |
| [chuan-code.md](chuan-code.md) | Quy ước cấu trúc thư mục và chuẩn code |
| [lo-trinh-du-an.md](lo-trinh-du-an.md) | Trạng thái hiện tại và lộ trình phát triển |

## Tóm tắt nhanh

Dự án chứng minh (POC) rằng dữ liệu vận hành (OLTP) có thể:

1. Được trích xuất tăng dần (incremental) từ PostgreSQL bằng **Polars** (engine Rust).
2. Đổ vào một **lakehouse Iceberg mở** trên object storage **MinIO**, với catalog
   **Lakekeeper** (REST, viết bằng Rust).
3. Được làm sạch / tổng hợp qua mô hình **medallion** (bronze → silver → gold).
4. Được truy vấn qua **Trino** và trực quan hóa bằng **Superset**.
5. Toàn bộ chuỗi ELT được điều phối tự động bằng **Apache Airflow**.

Tất cả chạy được trên laptop chỉ với `docker compose`.
