# Rust Lakehouse POC: Honest Reckoning on Scope, Gaps, and Unverified Runtime

**Date**: 2026-06-13 10:35  
**Severity**: Medium (runtime unverified, Iceberg write gap exposed)  
**Component**: End-to-end ELT pipeline (Postgres → Polars → Iceberg → Trino → Superset, Airflow-orchestrated)  
**Status**: Code-complete, pre-runtime validation

---

## What Happened

Completed design + full implementation of a 7-service docker-compose lakehouse POC in one day. The user asked for a "Rust-accelerated" warehouse; we built it, but discovered and **honestly documented** that production-grade Rust Iceberg writes do not exist yet (2026). All writes route through PyIceberg (Python). The POC is real code, not a mockup — 2 researcher reports, 1 red-team, full code review, passing unit tests — but **Docker daemon was down at session end, so live runtime verification never ran**.

---

## The Brutal Truth

This stings because we came *so close* to a clean story. The plan is technically sound, the code compiles and unit-tests pass, but I'm sitting here unable to verify the most critical claim: "does data actually flow end-to-end?" Docker was offline. We did not force-run it. The acceptance criteria — `parquet files land in MinIO, Iceberg snapshots increment, Trino queries return rows` — remain **unverified assumptions**.

Worse: the user's original ask ("Rust-accelerated") turned out to be a misnomer the moment we opened the Iceberg docs. Polars is genuinely Rust. Lakekeeper (catalog) is Rust. But writing to Iceberg from Rust? Doesn't exist in production. We caught this during red-team review, escalated it honestly (did NOT pretend PyIceberg was acceptable without disclosure), and the user chose to proceed anyway. That's fine — I documented the gap and a DuckDB fallback. But it's a gap. And it stays a gap until someone funds the Rust Arrow IPC layer.

---

## Technical Details

**Code Status:**
- 7/7 pure-Polars transform unit tests pass (bronze append-only, silver dedup, gold marts)
- Docker Compose config validates cleanly (both MVP and full profiles)
- Python bootstrap and DAG orchestration compile; no syntax errors
- Watermark schema, checkpoint logic, incremental boundary all present and testable

**Unverified Paths:**
- `services-healthy` (OrbStack daemon down)
- `psql data lands → Iceberg catalog snapshot increments → Trino query succeeds` — never ran
- Lakekeeper management API JSON shape (guessed from docs, not tested live)
- Superset CLI registration (prepared but not executed)
- Rolling image tag resolution (lakekeeper, minio)

**What Red-Team Caught (and We Fixed):**
1. **CRITICAL**: Plan thesis leaned on unvalidated PyIceberg upsert. Fixed: bronze append-only, dedup in silver defers upsert risk.
2. **CRITICAL**: RAM budget was fiction (4 Postgres containers in diagram, actually shared single meta-db). Honest: 11–13 GB peak, ~6–7 GB MVP.
3. **CRITICAL**: Trino S3 vs REST properties mixed two Iceberg catalog generations. Fixed: unified REST-only path.

**What Code-Review Caught (and We Fixed):**
1. **CRITICAL**: Bronze schema inferred from first batch, drifted on run 2. Fixed: cast each delta to the table's Arrow schema.
2. **CRITICAL**: No try/except on transform steps. Fixed: per-table error handlers, fail-at-end.
3. **CRITICAL**: Watermark store is an unlocked read-modify-write race. Fixed: max_active_runs=1 on the DAG.

---

## Root Cause: Scope Discipline vs. Verification Gap

We cut ruthlessly — no Debezium, no Kafka CDC, no Spark, no ClickHouse (saved ~2 GB + 3 containers). That was honest YAGNI. But we did NOT cut the runtime acceptance test, which means **the entire pipeline is a hypothesis**. Everything *should* work. The unit tests prove the Polars logic. The config is valid. But "should" is not "does."

The deeper lesson: a full-stack system is a **configuration integration**, not a code integration. Passing unit tests is table stakes. Passing live is the actual bar.

---

## Next Steps

1. **Immediate**: Restart Docker, run `docker-compose up` (both profiles), verify services healthy, land one batch end-to-end, confirm Iceberg snapshots increment, query Trino.
2. **If live fails**: debug per service; likely candidates are Lakekeeper management API JSON shape, connectorx Arrow dtype coercion, or Superset CLI scope.
3. **If live succeeds**: document the happy path, add incremental test data (rolling watermark), verify idempotence.
4. **Rust gap**: open an issue to track "Rust native Iceberg write library" as a future dependency; for now, PyIceberg is the documented path.

---

## Lessons Extracted

- **Scout with `find`, not `ls`**: Under the context hook, `ls` output gets filtered. Use `find | wc` to verify repo shape. (Caught: this is a 100+ subproject monorepo; POC should live in `sample-poc/`, not root.)
- **"Rust-accelerated" is not "all Rust"**: Honesty beats hype. Documented the write gap without pretense.
- **Unit tests ≠ integration validation**: Polars logic is proven. Config is valid. Data flow is still a bet.
- **Review gates work**: Red-team and code-review caught 6 criticals before code merged. That's the point.

---

## Unresolved Qs

- Does Lakekeeper REST API JSON match the bootstrap.sh assumptions?
- Does connectorx preserve Arrow dtypes on Postgres→Polars EXTRACT?
- Does Docker on this machine have sufficient resources for 7 concurrent services?
