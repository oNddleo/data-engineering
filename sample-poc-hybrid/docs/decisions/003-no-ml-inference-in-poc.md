# ADR-003 — No ML inference on images/videos in the POC

**Status:** Accepted.
**Date:** 2026-06-19 (initial planning).

## Context

Image + video payloads naturally invite ML workflows: object detection (YOLO), OCR, scene classification, speech-to-text (Whisper). The hybrid POC could either:

1. Stop at storage + metadata + thumbnail (EXIF, ffprobe).
2. Add an ML inference stage that writes detected classes / transcripts back into silver.

## Decision

**Stop at metadata + thumbnail.** No ML in this POC.

## Rationale

- Resource budget. A 16 GB laptop already hosts Spark + Kafka + Postgres + Hive + Trino + Superset + Airflow. Adding a CUDA-less PyTorch worker would crowd the same RAM and confuse the message: this POC is about lakehouse mechanics, not model serving.
- Model selection is a separate planning exercise. YOLOv11 vs DETR vs custom; CPU vs GPU runtimes; batch vs streaming inference; MLflow vs Bento — each cell of that matrix could justify its own POC.
- The lakehouse mechanic — storing image/video as binary in MinIO, deriving metadata in Spark, registering in HMS — is the same whether the downstream consumer is a BI dashboard or a model serving job. Get that right first.

## Consequences

- `bronze.media_objects` carries `thumbnail_key`, EXIF, and ffprobe metadata — no model output columns.
- A follow-up plan can append an `silver.media_classifications` Delta table; the joining key (`object_key`) is already stable.
- ML platforms that *would* fit later: MLflow (already in Databricks-aligned story), Triton Inference Server, or a Spark Pandas UDF wrapping a model in a future Phase 10+.
