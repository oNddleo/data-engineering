---
phase: 6
title: Gold - Marts & Cross-Domain Aggregates
status: completed
priority: P2
effort: 1d
dependencies:
  - 5
---

# Phase 6: Gold - Marts & Cross-Domain Aggregates

## Overview

Tạo các bảng gold phục vụ BI: aggregate hourly/daily IoT, device health KPI, media storage usage, và **cross-domain join** (sự kiện IoT gần thời điểm chụp media của cùng device) — chứng minh giá trị hybrid IoT + multimedia trong cùng 1 lakehouse.

## Requirements

- **Functional**: gold incremental, rebuild được; SLA freshness ≤ 5 phút sau silver.
- **Non-functional**: bảng gold ≤ 100 MB cho POC; partition theo `date` để Superset filter nhanh.

## Architecture

```
silver.iot_readings ──► gold.iot_hourly_metrics  (avg, min, max, p95, count theo device+sensor+hour)
                  ├──► gold.device_health        (last_seen, missing_minutes, anomaly_rate_24h)
                  └──┐
                     ▼ join window ±5 phút theo device_id
silver.media_catalog ──► gold.iot_media_correlation
                  └──► gold.media_storage_daily  (bytes_per_type_per_day, file_count, top_devices)
```

**gold.iot_hourly_metrics**: `device_id, sensor_type, hour_ts, avg_value_si, min_value, max_value, p95_value, sample_count, outlier_count, location_city, owner_org`.
**gold.device_health**: `device_id, model, last_seen_ts, lag_minutes, anomaly_rate_24h, signal_quality_score`.
**gold.iot_media_correlation**: `device_id, media_object_key, media_type, taken_at, nearest_iot_event_id, value_delta_5min`.
**gold.media_storage_daily**: `dt, media_type, file_count, total_bytes, top_devices ARRAY<STRUCT<device_id, files INT>>`.

## Related Code Files

- Create: `pipeline/spark_jobs/build_gold_iot_hourly.py`
- Create: `pipeline/spark_jobs/build_gold_device_health.py`
- Create: `pipeline/spark_jobs/build_gold_media_storage.py`
- Create: `pipeline/spark_jobs/build_gold_iot_media_correlation.py`

## Implementation Steps

1. `build_gold_iot_hourly.py`:
   - Đọc silver `event_date >= today - 7`.
   - `groupBy("device_id","sensor_type", date_trunc("hour","event_ts"), "location_city","owner_org")`.
   - Agg: `avg`, `min`, `max`, `percentile_approx(0.95)`, `count`, `sum(quality_flag='outlier')`.
   - MERGE INTO gold theo PK `(device_id, sensor_type, hour_ts)`.
2. `build_gold_device_health.py`:
   - Window cuối cùng: `max(event_ts) AS last_seen_ts`, `current_timestamp() - last_seen_ts AS lag`.
   - Anomaly rate: `count(quality_flag='outlier')/count(*) WHERE event_ts >= now()-24h`.
   - Overwrite full mỗi run (bảng nhỏ).
3. `build_gold_media_storage.py`: groupBy(taken_date, media_type) → sum size + count + top-N device qua `collect_list` + sort.
4. `build_gold_iot_media_correlation.py`:
   - `as-of join`: với mỗi media row, tìm IoT event cùng `device_id` có `|event_ts - taken_at| ≤ 5 min`, lấy event gần nhất theo abs(diff).
   - Triển khai bằng window function thay vì cross join (tránh tích Descartes).

## Success Criteria

- [ ] `gold.iot_hourly_metrics` có row tương ứng số `(device, sensor, hour)` distinct trong silver.
- [ ] `gold.device_health` đếm = 100 (toàn bộ thiết bị).
- [ ] `gold.iot_media_correlation` non-empty (≥ 70% media match được IoT event lân cận, do data sinh cùng pool device_id).
- [ ] Trino query 3 gold trả về < 1s.

## Risk Assessment

- **As-of join nặng**: dùng `repartition("device_id")` + window thay vì range join.
- **Gold rebuild ghi đè concurrent với streaming**: orchestrator (phase 7) bảo đảm gold job chỉ chạy 1 lần/giờ, không xung đột streaming bronze.
