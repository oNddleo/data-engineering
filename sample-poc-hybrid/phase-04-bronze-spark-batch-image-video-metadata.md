---
phase: 4
title: "Bronze - Spark Batch Image/Video Metadata"
status: pending
priority: P1
effort: "1.5d"
dependencies: [1, 2]
---

# Phase 4: Bronze - Spark Batch Image/Video Metadata

## Overview

Job Spark batch quét MinIO bucket `raw-media/`, dùng **binaryFile data source** + **pandas UDF** để trích xuất metadata (EXIF với Pillow cho ảnh, ffprobe cho video) và tạo thumbnail (256x256 PNG). Metadata ghi vào Delta `bronze.media_objects`, thumbnail upload trở lại MinIO `thumbnails/`. Bronze chỉ chứa metadata + path tham chiếu, không lưu binary.

## Requirements

- **Functional**: incremental scan (so với watermark `_last_run_ts`), skip object đã xử lý theo `object_key + etag`.
- **Non-functional**: xử lý ≥ 1000 file < 5 phút trên 2 worker; thumbnail size ≤ 30 KB.

## Architecture

```
spark.read.format("binaryFile")
    .option("pathGlobFilter", "*.{png,jpg,jpeg,mp4}")
    .load("s3a://lakehouse/raw-media/")
    │
    ▼ join anti với bronze.media_objects ON object_key+etag  (incremental)
    │
    ▼ pandas UDF extract_metadata(content_bytes, path) -> Struct
    │    image branch: Pillow.open → exif → dict
    │    video branch: write tmp + ffprobe → JSON
    │
    ▼ pandas UDF make_thumbnail(content_bytes, type) -> bytes  (image: resize; video: ffmpeg -ss 1 frame)
    │
    ▼ upload thumbnail bytes lên MinIO key `thumbnails/{hash}.png`
    │
    ▼ writeDelta append → bronze.media_objects
```

**Bronze schema**:
- `object_key STRING`, `etag STRING`, `bucket STRING`, `media_type STRING (image|video)`,
- `mime STRING`, `size_bytes BIGINT`, `modified_at TIMESTAMP`,
- `image_meta STRUCT<width INT, height INT, exif STRING (JSON), taken_at TIMESTAMP, gps_lat DOUBLE, gps_lon DOUBLE>`,
- `video_meta STRUCT<duration_sec DOUBLE, codec STRING, bitrate BIGINT, fps DOUBLE, width INT, height INT>`,
- `thumbnail_key STRING`, `ingestion_ts TIMESTAMP`, `ingest_date DATE` (partition)

## Related Code Files

- Create: `pipeline/spark_jobs/batch_media_bronze.py`
- Create: `pipeline/spark_jobs/lib/media_extractors.py` (extract_image_meta, extract_video_meta, make_thumbnail)
- Create: `pipeline/spark_jobs/lib/minio_upload.py` (boto3 upload thumbnail bytes)
- Create: `pipeline/conf/batch_media_bronze.yaml`

## Implementation Steps

1. `media_extractors.py`:
   - `extract_image_meta(content: bytes) -> dict`: Pillow `Image.open(BytesIO)`, đọc `_getexif()`, decode `GPSInfo` thành lat/lon (DMS → decimal).
   - `extract_video_meta(content: bytes) -> dict`: ghi tmp file, gọi `ffmpeg.probe()` (subprocess ffprobe), parse `streams[0]`.
   - `make_thumbnail(content, kind)`: image resize 256x256 LANCZOS; video `ffmpeg -ss 00:00:01 -vframes 1 -vf scale=256:-1`. Return PNG bytes.
2. `batch_media_bronze.py`:
   - Đọc binaryFile, anti-join với Delta hiện tại (`spark.read.table("bronze.media_objects")`).
   - Pandas UDF (Arrow) chạy extractor; trả về StructType (image_meta hoặc video_meta nullable theo media_type).
   - Thumbnail UDF trả về key string sau khi upload thành công; failed → key NULL.
   - `df.write.format("delta").mode("append").partitionBy("ingest_date").saveAsTable("bronze.media_objects")`.
3. Watermark: ghi `_last_run_ts` vào Delta nội bộ `bronze._media_watermark` hoặc dựa hoàn toàn vào anti-join (đơn giản hơn).
4. Makefile: `make batch-media-bronze`.

## Success Criteria

- [ ] Sau seed 50 image + 10 video, job hoàn tất, bronze đếm 60 row.
- [ ] `thumbnails/` chứa 60 PNG, mở được trong MinIO console.
- [ ] Chạy lần 2 không sinh duplicate (anti-join hoạt động).
- [ ] Image có `taken_at` non-null cho ≥ 90% (EXIF có trong seeder).

## Risk Assessment

- **ffprobe yêu cầu binary ffmpeg trong Spark image**: bake ffmpeg vào `infra/spark/Dockerfile` (apt install).
- **Pandas UDF OOM khi file lớn**: cap `spark.sql.execution.arrow.maxRecordsPerBatch=100`; reject video > 50 MB.
- **EXIF orientation lệch thumbnail**: dùng `ImageOps.exif_transpose` trước resize.
