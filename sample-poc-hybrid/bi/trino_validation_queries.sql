-- ====================================================================
-- Trino validation queries — paste into `make trino-cli` after pipeline run.
-- Covers Phase 1 (catalog) through Phase 6 (gold marts) acceptance checks.
-- ====================================================================

-- Catalog wiring -----------------------------------------------------
SHOW CATALOGS;
SHOW SCHEMAS FROM delta;
SHOW TABLES FROM delta.bronze;
SHOW TABLES FROM delta.silver;
SHOW TABLES FROM delta.gold;

-- Bronze row counts --------------------------------------------------
SELECT count(*) AS bronze_iot_events_count FROM delta.bronze.iot_events;
SELECT count(*) AS bronze_media_objects_count FROM delta.bronze.media_objects;
SELECT
    media_type,
    count(*)        AS files,
    sum(size_bytes) AS total_bytes
FROM delta.bronze.media_objects
GROUP BY media_type
ORDER BY media_type;

-- Silver dedup proof -------------------------------------------------
-- distinct event_id == row count → dedup MERGE held the line.
SELECT
    count(*)                  AS rows,
    count(DISTINCT event_id)  AS distinct_event_ids,
    count(*) - count(DISTINCT event_id) AS unexpected_dupes
FROM delta.silver.iot_readings;

-- Outlier rate sanity (Phase 2 simulator targets ~1%) ----------------
SELECT
    sensor_type,
    count(*) FILTER (WHERE quality_flag = 'outlier') AS outliers,
    count(*) AS total,
    round(
        100.0 * count(*) FILTER (WHERE quality_flag = 'outlier') / count(*),
        3
    ) AS outlier_pct
FROM delta.silver.iot_readings
GROUP BY sensor_type
ORDER BY sensor_type;

-- Silver enrichment coverage -----------------------------------------
-- missing_dim should approach 0% once Phase 2 seed-oltp has run.
SELECT
    quality_flag,
    count(*) AS rows
FROM delta.silver.iot_readings
GROUP BY quality_flag
ORDER BY quality_flag;

-- Media catalog --------------------------------------------------------
SELECT
    media_type,
    count(*)                AS files,
    count(thumbnail_key)    AS files_with_thumbnail,
    avg(width)              AS avg_width,
    avg(height)             AS avg_height
FROM delta.silver.media_catalog
GROUP BY media_type
ORDER BY media_type;

-- Gold IoT hourly snapshot -------------------------------------------
SELECT
    device_id,
    sensor_type,
    date_format(hour_ts, '%Y-%m-%d %H:00') AS hour,
    round(avg_value_si, 2)                  AS avg_si,
    sample_count,
    outlier_count
FROM delta.gold.iot_hourly_metrics
WHERE hour_date >= current_date - interval '1' day
ORDER BY hour DESC, device_id, sensor_type
LIMIT 30;

-- Gold device health --------------------------------------------------
SELECT
    device_id,
    device_model,
    location_city,
    last_seen_ts,
    lag_seconds,
    events_24h,
    round(coalesce(anomaly_rate_24h, 0) * 100, 2) AS anomaly_pct_24h
FROM delta.gold.device_health
ORDER BY lag_seconds DESC NULLS LAST
LIMIT 20;

-- Gold media storage --------------------------------------------------
SELECT
    dt,
    media_type,
    file_count,
    total_bytes,
    top_device_id,
    top_device_files
FROM delta.gold.media_storage_daily
ORDER BY dt DESC, media_type;

-- Gold IoT⇄media correlation — proves the hybrid payoff ---------------
SELECT
    device_id,
    media_type,
    object_key,
    taken_at,
    nearest_sensor_type,
    round(nearest_value, 2)            AS nearest_value,
    seconds_between
FROM delta.gold.iot_media_correlation
WHERE nearest_event_id IS NOT NULL
ORDER BY abs(seconds_between)
LIMIT 20;
