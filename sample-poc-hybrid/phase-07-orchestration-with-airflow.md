---
phase: 7
title: "Orchestration with Airflow"
status: pending
priority: P2
effort: "1d"
dependencies: [3, 4, 5, 6]
---

# Phase 7: Orchestration with Airflow

## Overview

Điều phối 3 DAG: (1) **streaming supervisor** giữ Spark Structured Streaming IoT bronze chạy bền vững (restart khi fail), (2) **batch hybrid** chạy hourly: media bronze → silver IoT/media → gold, (3) **maintenance** chạy daily: OPTIMIZE + VACUUM + dataset metric report.

## Requirements

- **Functional**: DAG tự retry, có SLA alert; expose Spark UI link trong task log.
- **Non-functional**: chạy LocalExecutor, ≤ 1 GB RAM cho scheduler+webserver.

## Architecture

```
DAG 1: streaming_iot_bronze_supervisor   (schedule_interval=None, manual + sensor)
    └── SparkSubmitOperator (long-running)  →  on_failure: notify + auto retry 3x

DAG 2: hybrid_batch_pipeline              (schedule_interval="@hourly")
    ├── wait_for_kafka_producer (TimeDeltaSensor + Kafka lag check)
    ├── batch_media_bronze       (SparkSubmitOperator)
    ├── build_silver_iot         (SparkSubmitOperator)
    ├── build_silver_media       (SparkSubmitOperator)
    ├── build_gold_iot_hourly    (SparkSubmitOperator)
    ├── build_gold_device_health (SparkSubmitOperator)
    ├── build_gold_media_storage (SparkSubmitOperator)
    └── build_gold_correlation   (SparkSubmitOperator)

DAG 3: maintenance_daily                  (schedule_interval="0 2 * * *")
    ├── pause_streaming          (TriggerDagRunOperator → set DAG 1 paused) <!-- Updated: Validation Session 1 — pause streaming bookend per Q3 -->
    ├── wait_streaming_stopped   (PythonOperator: poll spark master REST API until no active app)
    ├── optimize_bronze_iot      (SQL via Spark)
    ├── optimize_silver_iot      (Z-ORDER)
    ├── vacuum_all               (RETAIN 168h)
    ├── data_quality_report      (Great Expectations checkpoint → write to MinIO)
    └── resume_streaming         (TriggerDagRunOperator → unpause + trigger DAG 1)
```

## Related Code Files

- Create: `orchestration/dags/streaming_iot_bronze_supervisor.py`
- Create: `orchestration/dags/hybrid_batch_pipeline.py`
- Create: `orchestration/dags/maintenance_daily.py`
- Create: `orchestration/dags/lib/spark_submit_defaults.py` (default jars, conf, master URL `spark://spark-master:7077`)
- Create: `orchestration/Dockerfile` (Airflow + providers)
- Create: `orchestration/requirements.txt`

## Implementation Steps

1. `spark_submit_defaults.py` export `SparkSubmitOperator` factory (Airflow 3.0 `airflow.providers.apache.spark.operators.spark_submit`) với conf:
   - `--master spark://spark-master:7077`, `--deploy-mode client`,
   - `--packages io.delta:delta-spark_2.13:4.0.0,org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0,io.unitycatalog:unitycatalog-spark_2.13:0.3.0`,
   - `--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension`,
   - `--conf spark.sql.catalog.unity=io.unitycatalog.spark.UCSingleCatalog`,
   - `--conf spark.sql.catalog.unity.uri=http://unity-catalog:8087`,
   - `--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000` (+ creds qua Airflow Connections).
   - **Airflow 3.0 DAG dùng `from airflow.sdk import dag, task`** (task SDK mới), `from airflow.sdk import Asset` cho dataset-aware scheduling.
2. DAG 1 streaming supervisor: `SparkSubmitOperator` với `--conf spark.driver.supervise=true`, task `execution_timeout=None`, retry 3 lần delay 5 phút. Trigger thủ công 1 lần đầu, sau đó DAG luôn "running".
3. DAG 2 hybrid_batch: `catchup=False`, `max_active_runs=1` (tránh OPTIMIZE đụng silver build), dependency tuyến tính như sơ đồ. SLA 30 phút.
4. DAG 3 maintenance: dùng `SparkSqlOperator` chạy `OPTIMIZE bronze.iot_events`, `VACUUM ... RETAIN 168 HOURS`. Great Expectations checkpoint định nghĩa expectation `iot.value` between min/max, `media_objects.thumbnail_key` not null.
5. Airflow Connections: `spark_default`, `minio_s3`, `postgres_oltp`.
6. Makefile: `make airflow-ui`, `make airflow-trigger DAG=hybrid_batch_pipeline`.

## Success Criteria

- [ ] 3 DAG xuất hiện trong Airflow UI, parse không error.
- [ ] Trigger `hybrid_batch_pipeline` end-to-end pass < 5 phút.
- [ ] Kill spark driver streaming → DAG 1 retry tự khôi phục, không cần user can thiệp.
- [ ] DAG 3 sinh GE report HTML trong `s3a://lakehouse/_quality_reports/`.

## Risk Assessment

- **SparkSubmitOperator yêu cầu spark-submit binary trong Airflow image**: cài `spark-client` minimal hoặc dùng `DockerOperator` gọi sang container spark-master.
- **Streaming DAG = anti-pattern Airflow**: chấp nhận cho POC; production thật nên dùng K8s Deployment hoặc Databricks Job continuous.
- **Concurrent OPTIMIZE vs streaming write**: DAG 3 maintenance bookend `pause_streaming` → `wait_streaming_stopped` → maintenance tasks → `resume_streaming` (Validation Session 1 — Q3 chốt phương án pause sequential thay vì rely on Serializable).
