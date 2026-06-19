---
phase: 5
title: Silver - Cleansing & Standardization
status: completed
priority: P1
effort: 1d
dependencies:
  - 3
  - 4
---

# Phase 5: Silver - Cleansing & Standardization

## Overview

Silver chuẩn hoá dữ liệu bronze: dedup theo PK + latest watermark, ép kiểu/unit, loại outlier IoT theo rule (giá trị nằm ngoài [μ-3σ, μ+3σ] của cặp sensor_type/device), enrich từ Postgres OLTP (devices, locations). Dùng **Delta MERGE INTO** để upsert idempotent + Z-ORDER theo cột truy vấn nóng.

## Requirements

- **Functional**: silver luôn phản ánh "latest per PK" + bản ghi sạch; chạy lại không sinh duplicate.
- **Non-functional**: job batch < 60s với 1 triệu row bronze; OPTIMIZE + Z-ORDER chạy hàng ngày.

## Architecture

```
bronze.iot_events ──┐
                    ▼  MERGE INTO silver.iot_readings
bronze.media_objects ─┐ (dedup by event_id; upsert latest by ingestion_ts)
                      ▼  MERGE INTO silver.media_catalog
oltp.devices ────────┐
oltp.locations ──────┴► broadcast join → enrich device_model, city, owner_org

Outlier filter (window over device_id, sensor_type, 1h rolling):
    abs(value - mean) > 3 * stddev  →  silver.iot_anomalies (separate table)
```

**silver.iot_readings**: bronze cols + `device_model`, `device_owner_org`, `location_city`, `value_si` (chuẩn hoá đơn vị về SI), `quality_flag STRING (ok|outlier|missing_dim)`.
**silver.media_catalog**: media_objects cols + `device_id` (nếu derive từ object_key), enriched device + location.
**silver.iot_anomalies**: snapshot outlier riêng để alert.

Partition silver: `event_date` (= date(event_ts)) cho iot, `taken_date` cho media.

## Related Code Files

- Create: `pipeline/spark_jobs/build_silver_iot.py`
- Create: `pipeline/spark_jobs/build_silver_media.py`
- Create: `pipeline/spark_jobs/lib/unit_normalizer.py` (map sensor_type+unit → SI)
- Create: `pipeline/spark_jobs/lib/dim_loader.py` (JDBC read devices/locations + cache)
- Create: `pipeline/spark_jobs/maintenance_optimize.py` (OPTIMIZE + ZORDER + VACUUM 168h)

## Implementation Steps

1. **Silver IoT**:
   - Read bronze incremental (CDF của Delta `readChangeFeed`) hoặc theo `ingest_date >= last_run_date`.
   - Window dedup: `row_number() OVER (PARTITION BY event_id ORDER BY ingestion_ts DESC)` = 1.
   - Normalize unit: UDF map `(sensor_type, unit) → value_si`.
   - Join broadcast `devices`, `locations` (qua `device_location`).
   - Outlier flag bằng `approxQuantile` hoặc window 1h.
   - `MERGE INTO silver.iot_readings t USING staged s ON t.event_id = s.event_id WHEN MATCHED AND s.ingestion_ts > t.ingestion_ts THEN UPDATE * WHEN NOT MATCHED THEN INSERT *`.
2. **Silver media**: dedup theo `object_key`, merge bằng `etag` để biết file đã đổi nội dung.
3. **Anomalies tách riêng**: filter `quality_flag = 'outlier'` → append vào `silver.iot_anomalies` (giữ history alert).
4. **Maintenance**: `OPTIMIZE silver.iot_readings ZORDER BY (device_id, event_ts)`; `VACUUM silver.iot_readings RETAIN 168 HOURS`.

## Success Criteria

- [ ] Run silver 2 lần liên tiếp → cùng row count, không trùng (idempotency).
- [ ] `silver.iot_anomalies` chứa ~1% bronze (khớp tỉ lệ outlier sinh ở phase 2).
- [ ] `silver.iot_readings` 100% có `device_model` non-null (enrichment thành công).
- [ ] OPTIMIZE giảm file count ít nhất 5x; query device_id điểm < 2s.

## Risk Assessment

- **MERGE chậm trên Delta partition lớn**: chia partition theo `event_date`, MERGE chỉ với partition liên quan (predicate pushdown).
- **Broadcast OOM nếu devices/locations lớn**: POC bounded (100 + 20), an toàn; document threshold.
- **CDF chưa enable trên bronze**: bật `delta.enableChangeDataFeed=true` tại Phase 3 table create.
