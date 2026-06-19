---
phase: 8
title: Query & BI (Trino + Superset)
status: completed
priority: P2
effort: 0.5d
dependencies:
  - 6
---

# Phase 8: Query & BI (Trino + Superset)

## Overview

Trino đọc Delta tables qua connector `delta_lake` + Hive Metastore; Superset kết nối Trino, bootstrap 3 dashboard reproducible từ JSON export: **IoT Live**, **Device Health**, **Hybrid IoT + Media**.

## Requirements

- **Functional**: dashboard load < 3s ở dataset POC (~1M row bronze, ~60 media object).
- **Non-functional**: cấu hình + dashboard versioned trong git (Superset import YAML/JSON).

## Architecture

```
Delta tables (s3a://lakehouse/{bronze,silver,gold}/...)
     ▲ catalog: delta (Hive Metastore Service)
     │
Trino (8085)
     ▲ JDBC
     │
Superset (8089) ── dashboards ──► users
```

`infra/trino/etc/catalog/delta.properties` (Trino 470 — primary: Unity Catalog OSS):
```
connector.name=delta_lake
delta.metastore=unity
delta.unity-catalog.uri=http://unity-catalog:8087
hive.s3.endpoint=http://minio:9000
hive.s3.path-style-access=true
hive.s3.aws-access-key=minioadmin
hive.s3.aws-secret-key=minioadmin
delta.enable-non-concurrent-writes=true
```

Fallback (`infra/trino/etc/catalog/delta_hms.properties` — chỉ enable khi profile `hms`):
```
connector.name=delta_lake
delta.metastore=thrift
hive.metastore.uri=thrift://hive-metastore:9083
hive.s3.endpoint=http://minio:9000
hive.s3.path-style-access=true
```

## Related Code Files

- Create: `bi/trino_validation_queries.sql` (smoke + sanity check sau pipeline)
- Create: `bi/superset/bootstrap.sh`, `bi/superset/dashboards/iot_live.yaml`, `device_health.yaml`, `hybrid_iot_media.yaml`
- Create: `bi/superset/datasets/*.yaml` (4 dataset: gold.iot_hourly_metrics, gold.device_health, gold.iot_media_correlation, gold.media_storage_daily)
- Create: `bi/superset/database.yaml` (Trino connection)

## Dashboards

1. **IoT Live**: line chart avg_value_si theo hour cho 4 sensor_type, top-10 device theo sample_count, big number panel "events last hour".
2. **Device Health**: table device_id × last_seen_ts × lag_minutes × anomaly_rate (heat row khi lag > 5 phút), map (lat/lon) trạng thái online/offline.
3. **Hybrid IoT + Media**: storage usage stacked bar theo media_type/ngày, table top-20 correlation event (device, media key thumbnail link, value_delta_5min), filter `media_type`.

## Implementation Steps

1. Smoke validate Trino: `SHOW SCHEMAS FROM delta; SELECT count(*) FROM delta.gold.device_health;`.
2. Superset bootstrap: `superset db upgrade && superset fab create-admin && superset init && superset import-dashboards -p dashboards/`.
3. Datasets yaml định nghĩa `cache_timeout: 30` (giây) cho IoT Live.
4. Thumbnail link: dataset `gold.iot_media_correlation` thêm calculated column `thumbnail_url = concat('http://localhost:9001/lakehouse/', thumbnail_key)`; chart "Table" cho phép HTML render.
5. Export lại sau khi build dashboard để versioned: `superset export-dashboards`.

## Success Criteria

- [ ] Trino đọc được toàn bộ delta tables (bronze/silver/gold) qua HMS.
- [ ] 3 dashboard hiển thị data sau pipeline run, chart không error.
- [ ] Thumbnail link click mở được image trong MinIO console.
- [ ] `bi/superset/dashboards/*.yaml` import lại sạch sau wipe Superset.

## Risk Assessment

- **Delta connector Trino chậm khi nhiều file**: chạy OPTIMIZE phase 7 trước; cache table stats bằng `ANALYZE`.
- **Superset chưa hỗ trợ Delta UniForm full**: dùng connector `trino` qua HMS (đã verified), không trực tiếp Delta.
- **CORS thumbnail từ MinIO**: set `MINIO_BROWSER_REDIRECT_URL` hoặc proxy qua nginx nếu cần.
