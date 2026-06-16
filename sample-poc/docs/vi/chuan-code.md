# Chuẩn code & cấu trúc dự án

## Cấu trúc thư mục

```
sample-poc/
├── docker-compose.yml      # tất cả dịch vụ (Airflow/Superset thuộc profile `full`)
├── Makefile                # task runner — `make help` liệt kê target
├── .env.example            # mẫu biến môi trường (KHÔNG commit .env thật)
├── infra/                  # bootstrap MinIO + Lakekeeper, cấu hình Trino
│   ├── minio/              # bootstrap.sh (tạo bucket)
│   ├── lakekeeper/         # bootstrap.sh (đăng ký warehouse)
│   ├── meta-db/            # init-databases.sql (DB cho lakekeeper/airflow/superset)
│   └── trino/etc/          # config + catalog iceberg.properties + smoke_test.sql
├── source/                 # schema.sql + seeder Faker (dữ liệu nguồn)
├── pipeline/               # ELT Polars/PyIceberg + transforms
│   ├── extract_load_bronze.py
│   ├── transform_silver.py
│   ├── transform_gold.py
│   ├── transforms/         # silver.py, gold.py (hàm thuần Polars)
│   ├── iceberg_catalog.py  # client RestCatalog (Lakekeeper + MinIO)
│   ├── io_iceberg.py       # read/write Iceberg
│   ├── watermark.py        # đọc/ghi watermark trên MinIO
│   ├── config.py           # TableSpec (PK + watermark_col mỗi bảng)
│   └── settings.py         # cấu hình từ biến môi trường
├── orchestration/          # image Airflow + DAG lakehouse_elt
├── bi/                     # bootstrap Superset + truy vấn Trino
├── tests/                  # test đơn vị transform
└── docs/                   # kiến trúc + runbook (+ docs/vi tiếng Việt)
```

## Quy ước đặt tên

- **Python:** `snake_case` cho file, hàm, biến (theo PEP 8). Ví dụ: `extract_load_bronze.py`,
  `dedup_latest()`.
- **Shell / config:** kebab-case hoặc tên theo công cụ (`bootstrap.sh`, `iceberg.properties`).
- **Markdown (docs/vi):** kebab-case, tên mô tả rõ mục đích (`cong-cu-su-dung.md`).
- **Bảng dữ liệu:** namespace medallion + tên bảng (`bronze.customers`, `gold.daily_revenue`).

## Nguyên tắc thiết kế code

1. **Hàm thuần cho transform.** `pipeline/transforms/silver.py` và `gold.py` là các hàm
   thuần trên `pl.DataFrame` — không I/O, không side effect → dễ test, dễ tái sử dụng.
2. **Không nhân bản logic.** Airflow DAG shell-out sang chính script pipeline thay vì viết
   lại transform. Một nguồn sự thật duy nhất cho logic ELT.
3. **Cấu hình qua biến môi trường.** `settings.py` đọc mọi endpoint/credential từ env.
   Mặc định là chạy từ host (localhost); trong container override bằng service-DNS.
4. **Xây catalog tập trung.** Mọi phase dựng `RestCatalog` qua `iceberg_catalog.get_catalog()`
   để cấu hình đồng nhất giữa ingest và transform.
5. **Cô lập lỗi theo bảng.** Một bảng lỗi khi ingest không làm hỏng các bảng khác và không
   đẩy watermark của nó.
6. **Đóng biên tin cậy.** Watermark được validate là timestamp hợp lệ trước khi nội suy vào SQL.
7. **Type hints + `from __future__ import annotations`** ở mọi module Python.

## Bí mật & an toàn

- **Không bao giờ commit** `.env`, khóa API, mật khẩu DB. Chỉ commit `.env.example`.
- Secret thật sinh bằng `openssl`/`Fernet` (xem hướng dẫn chạy).
- Lakekeeper mã hóa credential lưu trữ bằng `PG_ENCRYPTION_KEY` (32 byte).

## Quy ước commit (theo repo)

- Dùng conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Không tham chiếu tới mã phase/finding của plan trong tên file hay comment code — comment
  giải thích **lý do** (invariant, race, trade-off), không phải nguồn gốc plan.

## Kiểm thử

- Test đơn vị tập trung vào hàm transform thuần, chạy trong image runner (`make test`),
  không cần dựng cả stack.
- Đối soát end-to-end: truy vấn canary gold-vs-doanh-thu-dòng (xem `bi/trino_validation_queries.sql`).
