# Code Review — Phase 4 + 5 + 6 (media bronze, silver, gold)

Scope: `pipeline/spark_jobs/batch-media-bronze.py`, `build-silver-iot.py`, `build-silver-media.py`, 4 gold jobs, `lib/dim_loader.py`, `infra/spark/spark-defaults.conf`. Verified against committed source.

## CRITICAL

**C1. First-run race on silver/gold MERGE when staged is empty.**
`build-silver-iot.py:215-218`, `build-gold-iot-hourly.py:81-89`, etc. Pattern: `ensure_tables()` creates the Delta table, then `DeltaTable.forName(...).merge(staged)`. Empty `staged` MERGE is a no-op — safe. BUT: `ensure_tables` uses `CREATE TABLE IF NOT EXISTS` with `LOCATION`. If the warehouse path was previously wiped under MinIO without dropping HMS metadata (common during POC iteration), HMS still says the table exists but Delta `_delta_log` is gone → `DeltaTable.forName` throws `AnalysisException: is not a Delta table`. Mitigation: add a `try DeltaTable.forName / except → spark.sql("DROP TABLE IF EXISTS …"); ensure_tables` rebuild, or document `make reset-warehouse` as required after MinIO wipe.

**C2. `binaryFile` etag collision on same-second rewrites.** `batch-media-bronze.py:205` — `etag := date_format(modificationTime,'yyyyMMddHHmmss')`. Two rapid PUTs to the same key within one second produce identical etag → anti-join skips the second write → silver never sees the new bytes. For the POC's batch-generated media this is fine, but the moment anyone uses `mc cp --overwrite` to iterate on a single file during demo, the change is invisible until the next minute. Either include `length` in the etag (`concat(date_format(...), '-', length)`) or document the limitation prominently. Real risk during demo, not theoretical.

## HIGH

**H1. Outlier detection per-batch is statistically unsound.** `build-silver-iot.py:142-155`. Stats computed within the trailing-7d batch including the seeded outliers. With Phase 2's ~1% ±5σ outliers, batch stddev is inflated and 3σ threshold likely won't trip on the smallest outliers. Walk-through: simulator normal sd≈1, outlier offset≈5. Mix at 1% → batch sd ≈ √(0.99·1 + 0.01·25) ≈ 1.12. Outlier value=5 → z = 5/1.12 ≈ 4.5σ — still flags. Verdict: borderline-ok for ±5σ outliers, would silently miss ±3σ events. Recommended: persist per-(device,sensor) rolling stats in a `silver.sensor_baseline` Delta table and join, not recompute per batch. For POC, document the limitation in the phase doc.

**H2. `device_id` extraction from `object_key` collides with `dev-NNNN` substring anywhere in the path.** `build-silver-media.py:35` regex `(dev-\d{4})` runs against the full key. If the user ever drops a file at `raw-media/archive-of-dev-0001/dev-0002-xxx.png`, regex_extract returns first match → wrong device. POC seeder writes flat keys so this is currently fine, but anchor the regex: `^(?:.+/)?(dev-\d{4})-`.

**H3. Silver `taken_date` falls back to `modified_at` when EXIF taken_at missing, but bronze ingest also writes ingest_date partition.** `build-silver-media.py:124` `taken_date = coalesce(to_date(taken_at), to_date(modified_at))`. If neither is set (EXIF stripped + no S3 metadata), `taken_date` is NULL — Delta will create a `taken_date=__HIVE_DEFAULT_PARTITION__` partition. Gold media-storage groups by `taken_date` so a NULL bucket appears in Superset. Add explicit `.coalesce(F.current_date())` fallback or drop rows with NULL taken_date before write.

**H4. Gold `media_storage_daily.top_devices` uses `ARRAY<STRUCT>`.** `build-gold-media-storage.py:46-47`. Trino 470 + Hive Delta connector can read array-of-struct (returned as `ROW(...)` array). Superset's table chart renders it as a JSON blob string. Not broken, but the dashboard payoff (Phase 6 promise: "top devices") will look ugly. Recommend either (a) keep ARRAY for analytics + add `top_device_id` scalar column for chart, OR (b) explode to a separate `gold.media_storage_top_devices` long table.

## MEDIUM

**M1. Silver MERGE on iot_readings is correct for late-arriving rows.** `build-silver-iot.py:191` — `whenMatchedUpdateAll(condition="s.ingestion_ts > t.ingestion_ts")`. Verified: re-emitted event with higher ingestion_ts wins, equal ingestion_ts is a no-op (preserves first writer). Good.

**M2. Gold hourly MERGE rebuilds closed hours correctly.** `build-gold-iot-hourly.py:82-89`. Re-running over a closed window recomputes avg/min/max/p95 from current silver and `whenMatchedUpdateAll` overwrites — idempotent for backfills. ✔

**M3. `to_timestamp("ts")` failure → NULL event_ts.** `build-silver-iot.py:135`. Producer emits ISO-8601 with `Z` suffix (Phase 2 simulator). `to_timestamp` without explicit format parses ISO correctly. But if a future producer emits a TZ-bare local time, Spark interprets as session TZ (UTC inside container) → silent drift. Add `.withColumn("event_ts", F.to_timestamp("ts", "yyyy-MM-dd'T'HH:mm:ss[.SSS]X"))` to fail-loudly on format mismatch, or document the contract.

**M4. JDBC unbounded read on every silver run.** `dim_loader.py:32-65` pulls full devices/locations every batch. 100+20 rows fine for POC; flag for prod with `numPartitions` + `partitionColumn` or push to nightly broadcast-cache.

**M5. PG_OLTP env vars not exposed to spark-master/worker containers (`docker-compose.yml:13-17` x-spark-common only sets AWS_*).** Driver in spark-master falls back to defaults `oltpuser`/`oltppass` in `dim_loader.py:19-20`. These happen to match `.env.example` defaults — works only because defaults are baked. If a user overrides `PG_OLTP_PASSWORD` in `.env`, the override is loaded into postgres-oltp service but NOT into spark-master → JDBC auth fails. Fix: add `PG_OLTP_USER`, `PG_OLTP_PASSWORD`, `PG_OLTP_JDBC_URL` to x-spark-common `environment:` block.

**M6. `overwriteSchema=true` + `saveAsTable` on `gold.device_health`.** `build-gold-device-health.py:71-77`. Delta replaces both data and schema; HMS gets new metadata via DeltaCatalog. No detach risk with the Delta extension in place (verified in `spark-defaults.conf:7-8`). Compatible widening works; incompatible type changes drop the column and re-add — silent data loss for any column that flips type. Low risk because this job is the sole writer.

## LOW

**L1. Correlation join intermediate size (~1.8M rows).** Acceptable for POC laptop; AQE coalesces shuffle. Fine.

**L2. Lazy imports inside UDF bodies** (`batch-media-bronze.py:100,108,117-118`) — correct pattern for executor side-loading. Cold-start cost negligible at 60-row batches.

**L3. Bronze partition mismatch with downstream.** Bronze.media_objects is partitioned by `ingest_date`, silver.media_catalog by `taken_date`. Causes a shuffle on every silver build — fine for POC, document for prod.

**L4. `enriched.write.append`+`partitionBy("ingest_date")` after `CREATE TABLE ... PARTITIONED BY (ingest_date)`** — Delta ignores the writer's `partitionBy` when the table is already partitioned, so this is redundant but harmless.

## Failure modes for the first-run command sequence

`make seed-oltp && stream-iot-bronze && batch-media-bronze && build-silver && build-gold` — likely first-time failures, ranked:

1. **C2 surfaces only if user re-runs `seed-media` then `batch-media-bronze` within the same second** — invisible until next minute.
2. **C1 surfaces on second run after `make down -v`** — HMS still has table entries pointing at the wiped S3 path.
3. **`build-silver-iot` on empty bronze** — `read_bronze` returns 0 rows, `dedup_and_typecast` → empty, `tag_outliers` stats df is empty, left-join is empty, MERGE is no-op. Verified safe.
4. **`build-gold-iot-media-correlation` before silver.media_catalog has any taken_at-bearing row** → media filter `taken_at.isNotNull() & device_id.isNotNull()` reduces to 0 → empty MERGE → no-op. Safe.

## Recommended Actions

1. Fix M5 (PG env vars in compose) — silent break on credential override.
2. Document or fix C2 (etag-on-modtime) — demo-breaking footgun.
3. Add HMS-vs-warehouse reconciliation note in plan.md for C1.
4. Anchor regex in H2 — 1-line fix.
5. Decide top_devices shape (H4) before Phase 7 dashboard work.
6. Document outlier-detection caveat (H1) in phase-05 doc, defer rolling-baseline to prod hardening.

## Unresolved Questions

- Should Phase 7 dashboard treat `taken_date IS NULL` rows separately or drop them upstream? (related to H3)
- Is the EXIF-stripping `dev-NNNN`-anchored regex contract documented anywhere downstream uses depend on? (related to H2)
