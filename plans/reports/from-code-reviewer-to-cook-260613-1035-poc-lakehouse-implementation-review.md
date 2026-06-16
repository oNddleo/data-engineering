# Code Review — POC Rust-Accelerated Lakehouse (Phase 1-7)

Reviewer: code-reviewer | Date: 2026-06-13 | Scope: full project boot-readiness.
Weighting: runtime correctness + "will it actually run" > style. Fresh project (no regressions possible).

## Verdict (TL;DR)

**Conditionally sound to hand to user for a real boot — boots far enough to be debuggable, but will hit 2-3 known stumbles at the live-stack edges.** The pure-Python transform layer is correct and tested; the medallion logic, watermark design, append-only invariant, and reconciliation all hold up under static analysis. The risk concentrates at the PyIceberg↔Lakekeeper and PyIceberg-write boundaries, which cannot be confirmed without a live stack.

Acceptance criteria 1-5: all **met in code** (see end). The gaps are runtime-API-shape uncertainties, not design defects.

---

## CRITICAL — fix before boot

### C1. `table.append(arrow)` schema mismatch: connectorx decimals/timestamps vs created Iceberg schema — `extract_load_bronze.py:45-47`
Bronze table is created from the **first** delta batch's Arrow schema (`ensure_table(..., arrow.schema)`), then every subsequent `table.append(arrow)` must match that schema **exactly**. Two real hazards:
- **Decimal**: Postgres `NUMERIC(10,2)` → connectorx → Arrow `decimal128(10,2)`. PyIceberg maps decimal fine, but if any incremental batch comes back with a different precision/scale (e.g. an all-null column inferred as `float64`/`null`), `append` raises a schema-conflict `ValueError` and the run dies mid-pipeline.
- **Timestamp tz**: `TIMESTAMPTZ` → Arrow `timestamp[us, tz=UTC]`. Iceberg v2 stores `timestamptz`. Round-trips usually OK, but PyIceberg has historically rejected non-`us` units. connectorx emits `us` so this is likely fine — **flag as needs-live-verification**.

Concrete fix: define an explicit `pyarrow.Schema` per `TableSpec` (or pass `pyiceberg` `Schema`) instead of inferring from the first batch, and cast each delta with `arrow.cast(target_schema)` before `append`. This removes nondeterminism across incremental runs. At minimum, wrap `ingest_table` in try/except that prints the offending schema diff rather than dying silently.

### C2. No error handling anywhere in the pipeline runners — `extract_load_bronze.py`, `transform_silver.py`, `transform_gold.py`, `io_iceberg.py`
Zero try/except. Any single-table failure (catalog 4xx, S3 timeout, schema conflict from C1) aborts the whole run with a raw traceback. In Airflow each task is one `BashOperator` shelling the whole script, so a failure on table #4 leaves bronze partially appended AND the watermark un-advanced for the failed table (acceptable) — but `transform_silver` overwrites silver from whatever bronze state exists, so a partial bronze append silently produces a partial silver/gold. **This breaks the reconciliation invariant non-deterministically.** Add: per-table try/except in `ingest_table` that re-raises after logging which table/row-count failed; make the runner exit non-zero so Airflow marks the task failed (it will, since uncaught → exit 1, but partial-state is the real issue).

### C3. Watermark `set_many` is read-modify-write with no locking — `watermark.py:39-45`
`load_all()` → `current.update()` → `open("w")` overwrites the whole JSON object. Airflow `@hourly` + a concurrent manual `make ingest-bronze` (criterion 3 explicitly wants shared store) = lost-update race: whichever writes last clobbers the other's advances, silently rewinding a watermark and causing **duplicate bronze appends** on the next run. For a single-operator POC this is low-probability, but it's a real correctness bug given the design goal of a *shared* store. Minimum fix: document "single writer at a time" loudly; better: write to `watermarks.json.tmp` then atomic rename, and/or gate concurrency in the DAG (`max_active_runs=1`, already implied by catchup=False but not guaranteed). `max_active_runs=1` is the cheap correct fix — add it to the DAG.

---

## HIGH

### H1. SQL injection / correctness in watermark WHERE clause — `extract_load_bronze.py:23`
`f"WHERE {spec.watermark_col} > '{since}'::timestamptz"`. `since` comes from `watermark.get()` → the JSON in S3, and `spec.watermark_col`/`spec.name` come from `config.TABLES`. All three are developer-controlled constants today, so **not exploitable now**. But it's string-interpolated SQL into `pl.read_database_uri`, and `since` is externally-stored state (anyone with MinIO creds can write the watermark file). A crafted watermark value (`1970-01-01'; DROP …`) would inject. Fix: validate `since` parses as ISO-8601 before use (`datetime.fromisoformat(since)`), or pass it as a bound param. Low exploitability, real trust-boundary violation — flagging HIGH because the WHERE was explicitly called out for scrutiny.

### H2. `_read_delta` full-mode does `SELECT *` with no WHERE but bronze schema is first-batch-inferred — interacts with C1
Same root as C1. Also `SELECT *` pulls `created_at`/`updated_at` into bronze, which is fine, but means bronze schema includes columns silver/gold never use — acceptable for raw layer.

### H3. Lakekeeper bootstrap JSON shape is unverified against the running image — `infra/lakekeeper/bootstrap.sh:13-40`
**Needs-live-verification, NOT a bug.** The `/management/v1/bootstrap` and `/management/v1/warehouse` payloads (`storage-profile`, `storage-credential`, `flavor: minio`, `sts-enabled`) match Lakekeeper's documented shape circa 0.x but the image is pinned to `:latest` (.env.example:10) — the API may have moved. The script's own comment admits this. **Pin `LAKEKEEPER_IMAGE` to a concrete tag** and verify the JSON against that tag's `/swagger-ui`. The `curl -sf` + `|| echo continue` pattern will **mask a real 4xx** (it swallows failure and proceeds), so a bad warehouse registration won't fail the one-shot container — Lakekeeper will look healthy but `create_table` later 404s the warehouse. Change: on the warehouse-create call, do NOT swallow non-"already exists" errors; grep the response for a conflict signal before continuing.

### H4. `:latest` image tags defeat reproducibility — `.env.example:8-10`
`minio/minio:latest`, `minio/mc:latest`, `quay.io/lakekeeper/catalog:latest`. The file's own comment says "PIN these." A `latest` Lakekeeper especially is the single most likely thing to break the bootstrap (H3) on a future boot. Pin all three to digests or concrete tags before handing over.

### H5. Trino `discovery.uri=http://localhost:8080` — `infra/trino/etc/config.properties:5`
For single-node Trino this is the documented/correct value (the coordinator discovers itself on localhost inside its own container), so **not the localhost-vs-DNS bug** the criteria warn about — the catalog/S3 endpoints correctly use `minio:9000`/`lakekeeper:8181`. Noted to preempt a false-positive "fix." Leave as-is.

---

## MEDIUM

### M1. `top_customers` tie-order assertion is fragile — `tests/test_transforms.py:84` / `transforms/gold.py:53-58`
Test asserts `customer_id == [10, 20]` when both have LTV 30 (a tie). Polars `sort` is **not guaranteed stable** unless `maintain_order`/stable sort is in play; on a tie the order is an implementation detail. Test passes today but may flake across Polars versions. Fix: assert on the set `{10,20}` and `lifetime_value.sum()`, not positional order. (Test-only, not prod.)

### M2. `dedup_latest` uses `sort + unique(keep="last")` — correct but carries a subtle tz/NULL caveat — `transforms/silver.py:15`
`keep="last"` after ascending sort on `updated_at` = newest wins. Correct. Caveat: if `updated_at` has nulls, nulls sort first (so a null-updated row could win if it's the only one) — bronze schema has `updated_at NOT NULL`, so safe in practice. Also `unique` without `maintain_order` was given `maintain_order=True` — good, but that's a perf cost on large frames; fine for POC volumes. No change needed.

### M3. `daily_revenue` casts to Float64 → floating-point reconciliation risk at scale — `transforms/gold.py:10, 26`
Revenue computed in Float64 and `.round(2)`. The reconciliation test (`test_reconciliation`) sums tiny integers so it's exact, but at 200k orders Float64 accumulation can drift cents vs a Decimal sum, theoretically tripping a strict gold==silver check in `bi/trino_validation_queries.sql`. For BI-friendliness Float64 is a reasonable POC choice; just ensure the live validation query uses an epsilon, not strict equality. Needs-live-verification against the actual validation SQL.

### M4. `superset set-database-uri` is deprecated in Superset 4.x — `bi/superset/bootstrap.sh:19`
`superset set-database-uri` was removed/changed in newer Superset CLIs; on 4.1.1 it may not exist (the `||` fallback prints a manual instruction, so the container still succeeds). Needs-live-verification; the graceful fallback means it won't block boot. Also `sqlalchemy-trino` is deprecated in favor of the `trino` SQLAlchemy dialect (`trino://`) — you install both, which is fine.

### M5. Superset/Airflow share meta-db but `superset db upgrade`/`airflow db migrate` race on first `up-full` — both depend only on `meta-db` healthy, not on each other
They target different logical DBs (`airflow`, `superset`) so no table clash, but both run init concurrently against the same Postgres server. Low risk (separate DBs), noted for completeness.

### M6. `airflow-init` uses `airflow users create` — deprecated in Airflow 2.10 but still works; Airflow 3.x would break — `docker-compose.yml:178`. Pinned to 2.10.3 so OK. Don't bump Airflow major without revisiting.

---

## LOW

- **L1.** `iceberg_catalog.py:28` `ensure_namespace` does `(namespace,) not in catalog.list_namespaces()` — list_namespaces returns tuples; correct. Fine.
- **L2.** Hardcoded MinIO creds in `infra/trino/etc/catalog/iceberg.properties:22-23` (`minioadmin`) — Trino props can't read env easily, so this is pragmatic for a POC, but it desyncs if someone changes `.env`. Document the coupling.
- **L3.** `seed_append` calls `random.seed()` (line 119) for nondeterminism — intentional and documented. Fine.
- **L4.** No file exceeds 200 LOC. Largest: `docker-compose.yml` 265 lines (YAML, exempt), `seed_source_data.py` 180, `gold.py` 67. **Project 200-LOC rule satisfied** for all code files.
- **L5.** `.pyc` files are committed-on-disk in `pipeline/__pycache__` and `tests/` — gitignored (`*.py[cod]`) so won't be committed. Clean before handover anyway.
- **L6.** Trino healthcheck greps `'"starting":false'` from `/v1/info` — depends on exact JSON spacing; trinodb emits `"starting":false` with no space, so OK, but brittle. Acceptable.

---

## Real bug vs needs-live-verification

**Real bugs (fixable now, no stack):** C1 (schema inference nondeterminism), C2 (no error handling / partial-state), C3 (watermark race — add `max_active_runs=1`), H1 (watermark SQL trust boundary), H3-partial (bootstrap swallows 4xx), H4 (`:latest` tags), M1 (flaky tie test).

**Needs-live-verification (do NOT treat as broken):** Lakekeeper bootstrap JSON shape (H3), PyIceberg `create_table` from Arrow schema + `append`/`overwrite` against Lakekeeper, connectorx decimal/timestamp Arrow dtypes (C1 runtime half), `pl.from_arrow(scan().to_arrow())` round-trip dtypes, fsspec/s3fs watermark read/write against MinIO path-style, Superset `set-database-uri` on 4.1.1 (M4), Trino native-s3 + REST catalog wiring, Float64 reconciliation epsilon (M3).

---

## Acceptance criteria check

1. **Append-only + watermark-incremental bronze** — MET. `table.append` only; no upsert; watermark advances post-append; `--full` drops+reloads. (caveat C3 race)
2. **Silver dedup latest-per-PK; gold reconciles** — MET in code + 7 passing tests incl. reconciliation canary. `dedup_latest` correct.
3. **Manual + Airflow share pipeline code + watermark store** — MET. DAG shells the SAME `/opt/pipeline` scripts; same `settings.py` env-driven config; same S3 watermark JSON. (caveat C3)
4. **Service DNS + path-style S3** — MET. compose `*-env` anchors set `minio`/`lakekeeper`/`source-db`; `s3.path-style-access=true` in Trino props + PyIceberg + bootstrap. (Trino `discovery.uri=localhost` is correct single-node, not a violation — H5.)
5. **One shared meta-db, no 4× Postgres** — MET. `init-databases.sql` creates `lakekeeper`/`airflow`/`superset` logical DBs on the single `meta-db`; only `source-db` is separate (by design). 2 Postgres total, correct.

**Secrets:** `.env` is gitignored at monorepo root (`.gitignore:69`), project dir is fully untracked. No secret committed. `.env.example` ships only `change-me` placeholders. PASS.

---

## Top 3 must-fix before boot

1. **C1 — Pin bronze Arrow schema explicitly** (don't infer from first delta batch) so incremental `append` calls can't schema-conflict on a null/decimal-width drift. Biggest "works once then dies on run 2" risk.
2. **H3/H4 — Pin Lakekeeper (+ minio/mc) image tags and stop the bootstrap from swallowing 4xx.** A `latest` Lakekeeper with a moved management API + error-swallowing bootstrap = silently-broken warehouse that only surfaces as a `create_table` 404 deep in ingest. Pin + assert on bootstrap response.
3. **C2/C3 — Add per-table error handling in `ingest_table` and `max_active_runs=1` to the DAG.** Prevents partial-bronze→partial-gold silent reconciliation breakage and the shared-watermark lost-update race.

## Unresolved questions
- Exact connectorx Arrow dtype for `NUMERIC(10,2)` and `TIMESTAMPTZ` on the pinned Polars/connectorx versions — confirm on first live `make ingest-bronze`.
- Lakekeeper management API JSON shape for the pinned image tag.
- Does `bi/trino_validation_queries.sql` use strict `=` or an epsilon for the gold/silver reconciliation? (Not provided in review set — verify it tolerates Float64 drift.)
