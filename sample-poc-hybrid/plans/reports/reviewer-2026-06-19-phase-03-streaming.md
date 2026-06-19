# Phase 3 Review — Bronze Spark Structured Streaming IoT

Scope: `pipeline/spark_jobs/**`, `pipeline/conf/streaming-iot-bronze.yaml`, Makefile targets, docker-compose mount.
Verdict: ships, but two HIGH bugs will fail acceptance criteria as written.

## CRITICAL
None.

## HIGH

1. **Delta double-write on Kafka-DLQ failure** — `streaming-iot-bronze.py:178-190`. foreachBatch is at-least-once: if Delta append succeeds but `write_dlq` raises, Spark retries the whole batch and Delta gets duplicate valid rows (Delta append has no idempotency token here). Fix: pass `batch_id` through and use `.option("txnAppId", "iot-bronze-stream").option("txnVersion", batch_id)` on the Delta writer — Delta will skip already-committed batches. Required for acceptance "kill driver + restart → no dup".
2. **Silent-corruption rows pass the valid filter** — `streaming-iot-bronze.py:147` only checks `payload.event_id IS NULL`. A payload `{"event_id":"x"}` missing `device_id`/`sensor_type`/`value`/`unit`/`ts` parses to a struct with `event_id` set and the rest NULL, then lands in bronze with NULLs on schema-required columns. Filter on all `nullable=False` fields from `iot_schema.py:23-30`, or route the partial-record rows to DLQ.

## MEDIUM

3. **`write_dlq` triggers an extra Kafka job** — `dlq_writer.py:32` calls `.count()` after `take(1)`; both materialize the cached parsed batch twice before the actual write. Drop `count()`, write unconditionally after the `take(1)` probe, log batch_id only.
4. **`device_id` branch in DLQ key is dead code** — `dlq_writer.py:28` checks `"device_id" in df.columns` but `select_invalid` (`streaming-iot-bronze.py:167-169`) only projects `_raw_value`. Always `null`-keyed. Either drop the branch or key by `kafka_offset` so DLQ consumers get deterministic partitioning (your Q6).
5. **`BRONZE_AUDIT_COLUMNS` lists `_rescued_data` that the job never produces** — `iot_schema.py:43`. Drift between schema contract and writer. Remove or actually emit it via `columnNameOfCorruptRecord`.
6. **`stop-stream-iot` SIGTERMs the Python wrapper, not the JVM driver** — `Makefile:117`. `spark.streaming.stopGracefullyOnShutdown` only fires inside the JVM on a JVM-level shutdown hook. `pkill -TERM` on the Python script may exit before the JVM hook runs (depends on py4j gateway behavior). Safer: `pgrep -f 'org.apache.spark.deploy.SparkSubmit.*streaming-iot-bronze' | xargs -r kill -TERM`, then poll for exit.

## LOW

7. `ensure_bronze_table` CTAS + Delta `LOCATION` is fine on MinIO (strong consistency, your Q4) — confirmed safe. If location has prior Delta data, `CREATE TABLE IF NOT EXISTS` no-ops; if schema drifts, Hive will silently keep the old definition. Add a `DESCRIBE` + assert on first run.
8. Q3/Q8/Q9 confirmed safe. Q7: see #6.

Q10 most-likely first-run failure: bronze schema CREATE races HMS bootstrap if Phase 1's `metastore-init` hasn't created the `hive` DB yet — surface with `make hms-ready` gate.

Sources:
- pipeline/spark_jobs/streaming-iot-bronze.py:147,167-169,178-190
- pipeline/spark_jobs/lib/dlq_writer.py:24-43
- pipeline/spark_jobs/lib/iot_schema.py:23-44
- Makefile:117
