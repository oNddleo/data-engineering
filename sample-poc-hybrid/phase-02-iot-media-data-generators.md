---
phase: 2
title: IoT & Media Data Generators
status: pending
priority: P1
effort: 1d
dependencies:
  - 1
---

# Phase 2: IoT & Media Data Generators

## Overview

Tạo 3 loại data source synthetic để feed pipeline:
1. **IoT simulator** publish sensor reading → Kafka topic `iot.sensors`.
2. **Media uploader** đẩy ảnh/video synthetic vào MinIO bucket `raw-media/`.
3. **Postgres OLTP** seed bảng `devices`, `locations` để join chiều ở silver/gold.

## Requirements

- **Functional**: 1 script chạy được 3 chế độ (`--mode iot|media|all`), tham số chỉnh `--rate-per-sec`, `--duration`.
- **Determinism**: seed faker cố định, payload có `event_id` ULID để dedup được.

## Architecture

```
source/
├── iot_simulator.py        # producer Kafka, payload JSON Schema
├── media_uploader.py       # boto3 → MinIO, sinh PNG/JPG/MP4
├── seed_oltp.py            # Faker → postgres-oltp
└── schemas/
    ├── iot_event.avsc       # Avro schema reference
    └── media_object.json    # JSON schema reference
```

**IoT event payload**:
```json
{
  "event_id": "01J9X...",
  "device_id": "dev-0042",
  "sensor_type": "temperature|humidity|pm25|vibration",
  "value": 23.4,
  "unit": "C|%|ug/m3|mm/s",
  "lat": 21.0285, "lon": 105.8542,
  "ts": "2026-06-19T05:11:11Z",
  "fw_version": "1.2.3"
}
```

**Media object**: PNG/JPG sinh bằng Pillow (256x256, có EXIF DateTimeOriginal + GPSInfo); MP4 sinh bằng `ffmpeg -f lavfi -i testsrc -t 5` size ~1 MB. Naming: `raw-media/{type}/{yyyy}/{mm}/{dd}/{device_id}-{ulid}.{ext}`.

## Related Code Files

- Create: `source/iot_simulator.py`, `source/media_uploader.py`, `source/seed_oltp.py`
- Create: `source/schemas/iot_event.avsc`, `source/schemas/media_object.json`
- Create: `source/requirements.txt` (kafka-python, boto3, faker, pillow, ffmpeg-python, psycopg2-binary, ulid-py)
- Create: `source/schema_oltp.sql` (devices, locations, device_location)

## Implementation Steps

1. `iot_simulator.py`: dùng `confluent-kafka` ≥ 2.5 (tương thích Kafka 4.0 KRaft client protocol), `bootstrap.servers=kafka:9092`; loop sleep `1/rate`, sinh `device_id` từ pool 100 thiết bị, sensor random pick 4 type, value theo normal distribution + 1% outlier (>3σ) để test silver clean. Producer config `acks=all`, `enable.idempotence=true`, `compression.type=zstd`.
2. `media_uploader.py`: tham số `--count`, `--ratio image:video`; với image dùng Pillow set EXIF qua `piexif`; với video dùng `ffmpeg-python`, ghi tạm `/tmp` rồi upload bằng boto3 (`endpoint_url=http://minio:9000`).
3. `seed_oltp.py`: Faker sinh 100 `devices` (id, model, install_date, owner_org), 20 `locations` (lat/lon/city), join `device_location` (FK).
4. Makefile target: `seed-iot RATE=50 DUR=300`, `seed-media COUNT=80`, `seed-oltp`.

## Success Criteria

- [ ] `make seed-iot RATE=50 DUR=10` publish ~500 message, kafka-console-consumer đọc được.
- [ ] `make seed-media COUNT=50` tạo file trong MinIO console hiển thị đủ 50 object.
- [ ] `make seed-oltp` → `psql` đếm 100 devices, 20 locations.
- [ ] Có 1% outlier trong IoT event để verify silver loại được.

## Risk Assessment

- **Kafka producer block khi broker chưa ready**: retry exponential backoff, max 30s.
- **MinIO chậm với file lớn**: cap video duration 5s (~1 MB), batch upload concurrency = 4.
