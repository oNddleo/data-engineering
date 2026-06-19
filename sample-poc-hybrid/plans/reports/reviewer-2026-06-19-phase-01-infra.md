# Phase 1 Infrastructure Review — 2026-06-19

Adversarial review of the Phase 1 hybrid lakehouse infrastructure slice. Findings ranked by severity; each cites file:line. Verified against upstream Dockerfiles and Trino 470 docs (sources at end).

---

## CRITICAL — will block boot / fail smoke

### C1. Trino 470 does NOT recognize `delta.metastore=unity` / `delta.unity-catalog.uri`
- File: `infra/trino/etc/catalog/delta.properties:2-3`
- Trino 470's Delta connector only supports HMS (`hive.metastore.uri`) or AWS Glue (`hive.metastore=glue`). The `unity` metastore variant was added in a later OSS milestone / is a Starburst-only property. Source: Trino 470 docs (https://trino.io/docs/470/connector/delta-lake.html).
- Symptom: trino service log will print `Configuration property 'delta.metastore' was not used` and the `delta` catalog will fail to register → `SHOW SCHEMAS FROM delta` returns nothing (or errors). Phase 1 success criterion fails.
- Fix: ship the `delta_hms.properties.disabled` variant as the default (rename to `delta.properties`) and run with `--profile hms` for Phase 1. Move the UC-via-Trino experiment to a later phase or use a Trino fork that supports UC.

### C2. Unity Catalog server.properties + uc CLI mounted at wrong path
- File: `docker-compose.yml:175` mounts `/opt/unitycatalog/etc/conf/server.properties`
- File: `docker-compose.yml:176` mounts `uc-data:/opt/unitycatalog/etc/data`
- File: `infra/unity-catalog/bootstrap-catalogs.sh:9` invokes `/opt/unitycatalog/bin/uc`
- Upstream `unitycatalog/unitycatalog:0.3.0` installs into `/home/unitycatalog` (WORKDIR + USER `unitycatalog`). The `/opt/unitycatalog/...` paths do not exist in the image. Source: official UC Dockerfile.
- Symptom: server.properties is mounted into an empty path and the UC server falls back to defaults (H2 in-memory, not Postgres) → schema/catalog created by bootstrap is lost on restart; bootstrap script can't even invoke `uc` (file not found) → unity-catalog-bootstrap container exits non-zero, smoke fails.
- Fix: change every `/opt/unitycatalog/` to `/home/unitycatalog/` (compose volumes + bootstrap script). Verify the actual server.properties path by `docker run --rm --entrypoint sh unitycatalog/unitycatalog:0.3.0 -c "find / -name server.properties"` before pinning.

### C3. UC healthcheck uses `wget` but base image has no wget/curl
- File: `docker-compose.yml:178`
- UC 0.3 runtime stage is `alpine:3.20` with only `bash` installed (no curl, no wget, no busybox `wget` applet). Source: official UC Dockerfile.
- Symptom: healthcheck exits 127 forever → unity-catalog stays `unhealthy` → unity-catalog-bootstrap + trino never start → `make up-hybrid` never converges within 120s. Phase 1 healthy-≤120s criterion fails.
- Fix options: (a) extend the UC image with `apk add --no-cache curl` via your own Dockerfile; (b) switch healthcheck to `bash -c "</dev/tcp/localhost/8087"` which works in alpine bash; (c) `nc -z localhost 8087` after `apk add netcat-openbsd`.

### C4. Bitnami Spark `command:` override likely skips entrypoint setup
- File: `docker-compose.yml:231,255,270`
- Official bitnami/spark:4.x example uses default ENTRYPOINT (no `command:` override). The image's entrypoint.sh stages config, sets perms on `/opt/bitnami/spark/conf`, exports `SPARK_USER`, then execs run.sh. Calling `run.sh` directly bypasses that.
- Symptom (intermittent): mounted `spark-defaults.conf` may not be readable by `spark` user (perm 600 on first boot); deletion-vector defaults won't take effect; in some cases master starts but worker can't register due to missing Bitnami env normalization. May or may not surface in first smoke run.
- Fix: drop the `command:` override; let Bitnami's ENTRYPOINT pick up `SPARK_MODE`. Match the upstream example.

---

## HIGH — will not boot cleanly but recoverable

### H1. Postgres init script DROPs DB & GRANT race
- File: `infra/postgres/init-meta.sql:8-14`
- `docker-entrypoint-initdb.d/*.sql` runs ONCE on volume init (good). But `GRANT ALL ... TO metauser` against `metastore` DB is redundant (metauser is already owner via `POSTGRES_USER`). More importantly, `CREATE DATABASE ucatalog`/`airflow` run as `metauser` → owner of the new DBs is `metauser` — fine. Confirmed OK on re-read. No fix needed.
- Caveat: UC depends_on `postgres-meta: service_healthy`, and pg_isready returns healthy before init scripts finish in rare cases. Verify by checking `psql -c '\l'` shows `ucatalog` before UC connects. If race observed, add a wait-for-loop in UC bootstrap.

### H2. Kafka KRaft format runs `--config /opt/kafka/config/server.properties`
- File: `infra/kafka/format-storage.sh:18`
- The KAFKA_* env vars are translated into config by `/etc/kafka/docker/run` (the launch script) AFTER format. At format time, `/opt/kafka/config/server.properties` is the unmodified upstream sample (process.roles already set there for KRaft in 4.0, so format succeeds — but `log.dirs` in the sample is `/tmp/kraft-combined-logs`, NOT `/var/lib/kafka/data`).
- Symptom: format formats `/tmp/kraft-combined-logs` (sample default), then run.sh starts broker pointing at `/var/lib/kafka/data` (from `KAFKA_LOG_DIRS`) → broker complains the dir is not formatted → restarts in a loop OR formats a second time. Result is non-deterministic.
- Fix: format with explicit log dir flag and skip the config arg, e.g. `kafka-storage.sh format -t "$CLUSTER_ID" -c <(echo "process.roles=controller,broker"; echo "node.id=1"; echo "controller.quorum.voters=1@kafka:9093"; echo "log.dirs=$LOG_DIR")` OR mount a complete server.properties and let run.sh consume the same one. Simplest: render server.properties from env in the same script before formatting.

### H3. Trino discovery URI `localhost` survives because single-node — but breaks if you scale
- File: `infra/trino/etc/config.properties:4`
- Fine for now (single coordinator-only node). Flag for Phase 2 scaling. No action this phase.

### H4. minio-bootstrap is fire-and-forget; UC/Spark may race to write before bucket exists
- File: `docker-compose.yml:48-62, 165-183, 229-251`
- `unity-catalog` depends on `postgres-meta` only, not `minio-bootstrap`. `spark-master` depends on `minio: healthy` but minio is healthy as soon as the server is up — well before `minio-bootstrap` finishes `mb`. If UC tries to write its first table-default-location to `s3://lakehouse/...` before the bucket exists → 404 NoSuchBucket.
- Smoke test writes to `s3a://lakehouse/bronze/_smoke/...` which Spark creates on demand (S3a will create prefixes), so this is mostly a concern for UC's `s3.bucketPath.0=s3://lakehouse` registration. UC 0.3 lazily validates, so likely benign — but tighten by adding:
  ```yaml
  unity-catalog: depends_on: { minio-bootstrap: { condition: service_completed_successfully } }
  spark-master: depends_on: { minio-bootstrap: { condition: service_completed_successfully } }
  ```

---

## MEDIUM — quality / robustness

### M1. Spark healthcheck uses `curl` from the custom image (OK), but spark-worker has no healthcheck → `up-full` worker-2 may start before worker-1 is ready
- File: `docker-compose.yml:253-282`
- Workers don't gate other services, but adding `healthcheck` (curl `:8081` on worker) lets `make healthcheck` produce useful output.

### M2. Trino jvm.config 2GB heap + Spark master 1GB + Spark worker 2GB + UC ~1GB + 2×Postgres + MinIO + Kafka 2GB ≈ 11-12 GB
- Plan budget ≤ 12 GB; you'll be at the ceiling on a 16 GB laptop with OS+Docker overhead. Tight but feasible. Recommend lowering Spark worker default to 1.5G and Trino Xmx to 1.5G in `.env.example` for safety margin.

### M3. Healthcheck for hive-metastore is `nc -z localhost 9083` — port-open only, doesn't prove Thrift is serving
- File: `docker-compose.yml:218`
- Acceptable for fallback profile. If used, upgrade to `beeline -u 'jdbc:hive2://localhost:9083' -e 'show databases'`.

### M4. Trino healthcheck regex `'"starting":false'` is brittle
- File: `docker-compose.yml:299`
- The image ships `/usr/lib/trino/bin/health-check` — use that instead: `test: ["CMD", "/usr/lib/trino/bin/health-check"]`.

### M5. Spark `command: /opt/bitnami/scripts/spark/run.sh` is array form but already invoked by Bitnami ENTRYPOINT — see C4.

---

## LOW — POC hygiene

### L1. Static credentials in `.env.example` (minioadmin/minioadmin, admin/admin) — acceptable for POC, but call out in README that `.env` MUST be regenerated before any non-local deploy and that `.env` is in `.gitignore`. Verified `.env.example` line 50 already labels them.

### L2. KAFKA_CLUSTER_ID hardcoded to a sample value
- File: `.env.example:78`
- Comment instructs regeneration via `make kafka-id`. Fine. Consider failing loudly in format-storage.sh if the user leaves the placeholder.

### L3. Smoke script uses `mode("overwrite")` + `option("path",...)` + `saveAsTable` — UC OSS 0.3 has historically required EITHER managed (no path) OR external (with path AND no saveAsTable). Watch for `IllegalArgumentException: Cannot specify both path and table name` at smoke time; fall back to two-step: `CREATE TABLE ... USING DELTA LOCATION ...` then `INSERT OVERWRITE`.
- File: `infra/spark/scripts/smoke-test.py:55-60`

---

## Cross-cutting

- All inter-service hostnames use service DNS (kafka, minio, unity-catalog, spark-master, postgres-meta) — verified no leftover `localhost` except trino's own `discovery.uri` (intentional, single-node).
- No leaked secrets in compose files; `.env` is git-ignored (assumed; verify in Phase 9).

---

## Recommended actions (priority order)

1. **C1 — fix Trino delta catalog**: default to HMS variant; document UC variant as experimental.
2. **C2 — fix UC mount paths**: `/opt/unitycatalog` → `/home/unitycatalog` everywhere.
3. **C3 — fix UC healthcheck**: switch to `bash -c "</dev/tcp/..."` or bake curl in.
4. **C4 — drop Spark `command:` override** to match Bitnami expectations.
5. **H2 — fix Kafka format log-dir mismatch.**
6. **H4 — add `depends_on: minio-bootstrap: service_completed_successfully`** to UC and Spark.
7. M1-M4 — polish healthchecks.

---

## Unresolved questions

- Does Trino 470 have a vendor-specific patch that recognizes `delta.metastore=unity`? Confirm by `docker run --rm trinodb/trino:470 cat /usr/lib/trino/plugin/delta-lake/README` or release notes before fully discarding the UC-via-Trino path.
- Does UC 0.3.0's server.properties actually live at `etc/conf/server.properties` relative to `$HOME`, or is it elsewhere (e.g. `etc/server.properties`)? Spot-check before re-mounting.

---

## Sources

- [Trino 470 Delta Lake connector docs](https://trino.io/docs/470/connector/delta-lake.html)
- [Apache Kafka Dockerfile (trunk)](https://github.com/apache/kafka/blob/trunk/docker/jvm/Dockerfile)
- [Unity Catalog Dockerfile (main)](https://github.com/unitycatalog/unitycatalog/blob/main/Dockerfile)
- [Bitnami Spark docker-compose example](https://github.com/bitnami/containers/blob/main/bitnami/spark/docker-compose.yml)
- [Kafka 4.1 official Docker getting started](https://kafka.apache.org/41/getting-started/docker/)
