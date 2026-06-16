# Red-Team Adversarial Review — POC Rust Lakehouse End-to-End

**Date:** 2026-06-13
**Reviewer role:** hostile adversary. Goal: find what makes this FAIL/slip/mislead.
**Plan under review:** `plans/260613-1035-poc-rust-lakehouse-end-to-end/` (plan.md + phase-01..07)
**Ground truth:** the two researcher reports in `plans/reports/`.

Verdict up front: **the slice is buildable, but three load-bearing claims are unproven and one is contradicted by the plan's own research. Needs targeted rework before cook, not a full redo.**

---

## CRITICAL

### C1 — PyIceberg `upsert` is the linchpin of the incremental thesis, and it is the weakest tool in the stack
- **Phase:** 3 (steps 3, 6; success criterion "writes ONLY new/changed rows"), cascades to 4, 5, 7.
- **Risk:** The headline success criterion of the whole POC — "second DAG run ingests only new/changed rows (incremental proven)" (plan.md L87) — depends on `table.upsert(arrow, join_cols=[pk])`. The maturity report validates ONLY append for Rust; PyIceberg upsert exists (≥0.8) but is the least-exercised path. PyIceberg upsert does a full-table scan + anti-join + delete-files + append on EVERY run. On 1.5M order_items it is slow, memory-heavy, and a known source of correctness bugs (duplicate key handling, null join keys, type-mismatched join cols silently producing 0 matches → full re-insert → duplicate explosion).
- **Evidence:** maturity report §1 "Upsert pipelines do NOT work" (pure Rust); §6 "Iceberg upsert in pure Rust doesn't exist"; the docker reference report's own pseudo-code (report-2 L83-91) writes **append/overwrite parquet, never upsert**. So neither research artifact actually validated the upsert path the plan hinges on.
- **Why the plan's mitigation is insufficient:** Phase 3 risk note offers "fall back to append-only bronze + dedup in silver." That is the correct path — but it is buried as a fallback. If you fall back, then bronze is append-only and the "delta-only WRITE" success criterion (P3) is FALSE — bronze still grows by appending the delta, and "only changed rows written" is satisfied by the *extract filter*, not upsert. The plan conflates "extracted only the delta" (watermark, easy, real) with "applied an upsert merge" (hard, fragile). These are different claims and the acceptance criteria don't distinguish them.
- **Fix (must-fix):** Make append-only bronze + silver-dedup the **primary** design, not the fallback. Redefine the incremental success criterion as: "second run's extract SELECT touches only rows with updated_at > watermark, verified by row count of the bronze snapshot's added-records == size of the seeded delta." Drop `upsert` from the critical path entirely. If you keep upsert, add a Phase-3 spike task that proves it on full volume BEFORE Phase 4/5 build on it.

### C2 — RAM budget is fiction once you count every container; 4 Postgres instances now exist
- **Phase:** 1, 5, 6 (plan.md L79 "≥10GB"; report-2 §8).
- **Risk:** Plan says "8–10GB total." Actual container census the plan now mandates: source-db Postgres, **catalog-db Postgres** (P1 L31), Trino (2-3GB), MinIO (0.5-1GB), Lakekeeper (0.3GB), **airflow-metadata Postgres** (P5), airflow-scheduler, airflow-webserver, **superset-metadata Postgres** (P6), superset (1-1.5GB), plus mc init. That is **4 Postgres servers + Trino + Airflow(2 procs) + Superset + MinIO**. Report-2's 8-10GB estimate (L344) does NOT include the catalog-db Postgres, the airflow-metadata Postgres, or the superset-metadata Postgres as separate line items — it assumed Lakekeeper bundles SQLite and Airflow/Superset metadata share one Postgres. The plan split them all out. Real footprint is 11-13GB peak when a Trino join + a Polars 1.5M-row collect + Airflow task run concurrently.
- **Evidence:** report-2 L344 "8-10GB ... tight on 8GB" — and that line item table has NO catalog-db row and ONE Postgres row, not four. plan.md L79 claims the same 8-10GB while having added 3 extra Postgres.
- **Fix (must-fix):** (a) Use Lakekeeper's bundled/embedded metadata or point catalog-db, airflow-meta, superset-meta at a SINGLE shared Postgres with 3 databases — kills 2 containers. Report-2 L113 explicitly says Lakekeeper "bundles SQLite; no external metadata DB required" — Phase 1's dedicated catalog-db Postgres directly contradicts the cited research. Resolve which is true. (b) State a REAL peak-RAM number from `docker stats` during a DAG run, not idle sum. (c) Make Superset's drop-to-fallback a hard gate at 14GB, not "if tight."

### C3 — Trino S3/REST property names are inconsistent between the plan and its own research; one config is wrong and will fail at first table write
- **Phase:** 1 (steps 3, L51-57).
- **Risk:** Phase 1 uses `fs.native-s3.enabled=true`, `s3.endpoint`, `s3.path-style-access`, `s3.aws-access-key`. Research report-2 (L237-242) uses `fs.s3.endpoint`, `fs.s3.path.style.access`, `fs.s3.aws.access-key-id`. These are two DIFFERENT Trino filesystem config generations (legacy Hive `fs.s3.*` vs new native `fs.native-s3.*` with `s3.*` keys). Mixing them, or pairing the wrong endpoint key with the wrong filesystem toggle, yields a Trino that boots healthy (healthcheck `/v1/info` passes) but throws `S3 endpoint not configured` / `path-style` errors ONLY when the first Iceberg table commit hits MinIO — i.e. the healthcheck is green but Phase 1 success criterion "creating a throwaway table writes Parquet to s3://warehouse" fails. Worse, `iceberg.rest-catalog.warehouse=warehouse` (P1 L54) vs `s3://warehouse` (report-2 L236) — Lakekeeper expects a registered warehouse *name*, not an s3 URI; getting this wrong = "warehouse not found."
- **Evidence:** P1 L51-57 vs report-2 L233-242 — same purpose, divergent keys. Both cannot be correct for one Trino version.
- **Fix (must-fix):** Pin the EXACT Trino version first, then copy that version's documented native-S3 property set verbatim into one source of truth. Add a Phase-1 task that does a real `CREATE TABLE ... AS SELECT 1` and confirms a `.parquet` object appears in MinIO — the healthcheck is NOT sufficient acceptance.

---

## HIGH

### H1 — "Rust-accelerated" is marketing on the write/orchestrate path; Rust is marginal to what the POC actually proves
- **Phase:** thesis (plan.md L24-34), 3, 4.
- **Risk:** Honest accounting of where Rust does work: catalog (Lakekeeper, idle 150MB — not on the hot path), DB read (Polars/connectorx — real but Postgres I/O bound, not CPU bound at 1.5M rows), transforms (Polars — real). Every WRITE goes through PyIceberg (Python). Every orchestration step is Python. Trino (the query engine the user actually sees) is **JVM/Java**, not Rust. So the user-facing query layer and the entire write layer are not Rust. The transform layer (Polars) is the only genuine Rust acceleration, and at POC volume (seconds either way) it proves nothing about performance — pandas or DuckDB would finish just as fast on 1.5M rows.
- **Blunt argument the plan must answer:** **DuckDB would do reads + transforms + Iceberg writes in ONE in-process engine, also calls PyIceberg for writes, and is simpler than Polars-scan + PyIceberg-write plumbing.** The maturity report (§6) literally lists DuckDB as an equal-footing Iceberg write option and unresolved-Q4 asks "are you open to DuckDB." If the thesis is "open lakehouse end-to-end on a laptop," DuckDB+Trino+Superset proves it with fewer moving parts and no Polars↔PyIceberg Arrow-handoff bugs. Polars earns its place ONLY if you add a deliberate benchmark showing Rust transform speedup on a volume where it matters (10-50M rows) — which the plan does not do.
- **Fix:** Either (a) honestly rename the thesis to "open lakehouse, Rust where it's mature (catalog+transform)" and drop the performance implication — Phase 7 L42 already half-admits this, promote it to the plan title/thesis; OR (b) add one micro-benchmark task (Polars vs pandas on the gold aggregation at 10M rows) so "Rust-accelerated" is a measured claim, not a vibe. As-is, a reviewer will call the title misleading.

### H2 — Polars `scan_iceberg` against Lakekeeper REST is asserted "mature/verified," but neither report verified THIS combination
- **Phase:** 4 (L48, L70-73 "Verified: Polars iceberg read is mature").
- **Risk:** Maturity report §3 verifies `scan_iceberg` works "with REST catalogs" generically. It did NOT test scan_iceberg → Lakekeeper specifically, nor scan_iceberg reading tables that PyIceberg wrote with delete-files (the upsert path in C1). Polars `scan_iceberg` historically needs the PyIceberg catalog object or a metadata path; passing it a live Lakekeeper REST URI + auth (Lakekeeper bootstrap requires an admin identity, report-2 L119) is a real integration with real failure modes (auth token, warehouse name resolution, S3FileIO creds passthrough). The "(Verified)" parenthetical in P4 overstates the research.
- **Fix:** Lower the confidence label. Keep the `pl.from_arrow(pyiceberg.scan().to_arrow())` fallback (already noted) but make it the DEFAULT read in `io_iceberg.read_iceberg` since PyIceberg is already a hard dep and is the proven read path against Lakekeeper. Drop the scan_iceberg dependency unless a spike proves it against Lakekeeper auth.

### H3 — Watermark correctness has an unhandled gap that silently loses rows
- **Phase:** 2, 3 (P3 L56 "advance watermark to max(updated_at) of the batch").
- **Risk:** Classic bug. If extract reads `WHERE updated_at > wm` at time T, but a transaction committed at updated_at=T-1ms AFTER the extract snapshot began (long-running write, or clock not monotonic across the append-seed and the extract), that row is < new watermark and never re-read → permanent silent loss. The plan's tie-break on PK (P3 L74) fixes equal-timestamp dupes but NOT in-flight commits with earlier timestamps. For a POC demo this likely won't fire, but the success criterion "incremental proven" is exactly what a skeptical reviewer will probe by counting rows — and an off-by-N will show.
- **Fix:** Either (a) accept and DOCUMENT the at-most-once-per-watermark limitation as POC scope, or (b) use `updated_at >= wm` with PK-level dedup in silver (idempotent, handles overlap). Since silver already dedups on PK+max(updated_at) per C1's recommended design, `>=` + dedup is free and correct. Pick (b).

### H4 — Phase 6 depends only on [4] but needs the DAG (Phase 5) to have produced gold for a reproducible demo
- **Phase:** 6 (frontmatter `dependencies: [4]`).
- **Risk:** P6 builds Superset on gold marts. Gold is produced by Phase 4 scripts manually OR Phase 5 DAG. P6 declaring dep on [4] only means someone could build BI before orchestration exists, then Phase 7's `make demo` (which drives gold via the DAG) changes how gold is produced — and the Superset import bundle may reference tables/snapshots that the DAG path regenerates differently (overwrite marts get new snapshot IDs). Low blast radius but the dependency graph is loose.
- **Fix:** Either add `5` to P6's deps, or explicitly state P6 builds against manually-run Phase-4 gold and is re-validated after Phase 5. Make `make demo` the single source of gold for the shipped bundle.

---

## MEDIUM

### M1 — 7 phases + Airflow + Superset + 3-layer medallion is a platform, not a POC
- **Phase:** all. The thesis ("raw data lands in Iceberg, is transformed in Rust, is queried+visualized") is proven by Phases 1→4 + a single Trino query. Airflow (P5) and the silver layer add operational realism but not thesis proof. Bronze→gold (2 layers) proves medallion; silver is gold-plating for a POC.
- **Risk:** scope creep eats the timeline (plan sums to ~7 days effort; "POC" implies <3). Each added container is a new failure surface for the <30min clean-room claim.
- **Fix:** MVP cut to prove thesis: P1, P2, P3(append-only), P4(bronze→gold, skip silver or fold dedup into gold), one Trino reconciliation query, ONE Superset chart. Make Airflow + silver + multi-chart dashboard explicit STRETCH. The plan already cut CDC honestly — apply the same discipline one level deeper.

### M2 — "<30 min clean-room reproduction" is optimistic given first-run image pulls + builds
- **Phase:** 7 (L19, success "reproduce in <30 min").
- **Risk:** Fresh machine: pull Trino (~1GB image), MinIO, Lakekeeper, Superset (~2GB), Airflow (~1GB) + **build** orchestration/Dockerfile (pip install polars+pyiceberg+connectorx+airflow — connectorx wheel build can be slow) + Superset Dockerfile. On a normal connection that's 15-25 min of pulls/builds BEFORE seed + 2 DAG runs. The 30-min budget assumes warm cache. report-2 L465-469 "1 hour to working end-to-end" — the research itself says an HOUR, the plan says 30 min.
- **Fix:** State two numbers: cold (~45-60min incl. pulls, per research) and warm (<30min). Pre-pin/pre-pull in a `make pull` target timed separately from `make demo`.

### M3 — Decimal/timestamp type drift Postgres→Arrow→Iceberg is named but not pinned with concrete types
- **Phase:** 3 (L57), 4. Price DECIMAL(10,2) in source; Arrow decimal128; Iceberg decimal(P,S). connectorx/Polars may map Postgres NUMERIC to Float64 by default (precision loss → revenue reconciliation off by cents → P4 "±0 exact match" FAILS). Timestamps: Postgres `timestamp` (no tz) vs `timestamptz` vs Iceberg `timestamp`/`timestamptz` — connectorx tz handling is a known footgun.
- **Fix:** Phase 3 must specify exact target Iceberg schema per column (decimal(10,2), timestamptz UTC) and assert no float coercion on the price column. The "±0 exact match" gold reconciliation is the canary — good — but it will fail silently as a few cents unless decimal is pinned. Add an explicit cast in the read.

### M4 — `make demo` idempotency vs gold `overwrite` + Airflow `start_date`/`catchup`
- **Phase:** 5, 7. `make demo` runs full→append→incr. If Airflow `catchup=False` + `@hourly` schedule, a second `make demo` within the hour or a re-trigger may collide with a scheduled run; gold `overwrite` from two concurrent runs (P4 risk note admits this) corrupts marts. POC runs sequential so low-prob, but `make reset` between demos is the only guarantee and that's not enforced in the `make demo` target.
- **Fix:** `make demo` should `make reset` first (P7 L37 says "idempotent from make reset" but the target should CALL reset, not assume it). Set schedule to manual-only (`schedule_interval=None`) for the POC; @hourly invites surprise concurrent runs during a live demo.

---

## LOW

### L1 — Image tags say "pin a tag" but no versions are chosen; "verified 2026" research used `:latest` everywhere (report-2 compose). Pin concrete versions now (Trino X, Lakekeeper 0.12.0, PyIceberg 0.x, Polars 1.x) so the property-name issue (C3) is resolvable. — Phase 1.
### L2 — Lakekeeper bootstrap (admin identity, report-2 L119) is not a step in Phase 1; warehouse registration (P1 L60) assumes a bootstrapped server. Add the `POST /management/bootstrap` call as an explicit init step or Lakekeeper rejects the warehouse-register call. — Phase 1.
### L3 — Superset SQLAlchemy URI: plan uses `trino://` (P6 L27); research uses `sqlalchemy-trino` pip dep. Modern Superset uses the `trino` dialect (pip `trino`), `sqlalchemy-trino` is deprecated. Pin the right driver or connection test fails. — Phase 6.
### L4 — No data volume control for the demo run vs the seed: 1.5M order_items through PyIceberg upsert (if kept) every DAG run will blow the "minutes" demo budget (P7 L63). Tie demo default volumes down hard. — Phase 2/7.

---

## Top 3 Must-Fix Before Cook
1. **C1 — Kill `upsert` from the critical path.** Make append-only bronze + silver-dedup the primary design; redefine the "incremental proven" criterion around the watermarked extract delta, not a merge. The entire POC headline rests on this and it's the least-proven tool.
2. **C2 — Fix the RAM lie + container sprawl.** Collapse 4 Postgres → 1 shared (or use Lakekeeper embedded metadata per the cited research), and publish a REAL peak `docker stats` number. As specced it likely exceeds 10GB and breaks the laptop premise.
3. **C3 — Pin one Trino version and ONE correct native-S3 + REST-warehouse property set,** then add a real "table write lands a .parquet in MinIO" acceptance check. The two configs in plan vs research can't both be right; the wrong one passes healthcheck and fails at first write.

## Blunt Verdict
**Sound skeleton, dishonest in three load-bearing spots, over-scoped by one layer.** The vertical slice is real and buildable — Trino+Iceberg+MinIO+Lakekeeper is the most-proven part (report-2 L46). But (a) the incremental thesis leans on PyIceberg upsert that neither research artifact validated, (b) the RAM budget doesn't survive counting the containers the plan itself adds, and (c) "Rust-accelerated" oversells a stack whose write + query + orchestration layers are Python/Java. Fix C1-C3, cut to the M1 MVP, and demote the Rust-performance claim to a measured benchmark or an honest "Rust where mature" framing. Then it's a defensible POC. Ship as-is and the first skeptic who counts rows or runs `docker stats` sinks it.

## Unresolved Questions
1. Does Lakekeeper 0.12.0 require an external Postgres (Phase 1) or bundle metadata (report-2 L113)? The two artifacts disagree — resolve before C2 fix.
2. Has anyone run PyIceberg `upsert` on Lakekeeper-cataloged tables at 1M+ rows? No evidence in either report. If not, C1 is not a "fallback," it's the only path.
3. Exact Trino version → which S3 filesystem property generation? (C3 blocks on this.)
4. Is DuckDB acceptable as the transform+write engine instead of Polars+PyIceberg (maturity report unresolved-Q4)? If yes, H1 collapses much of the plumbing.
5. Target Iceberg format v1 or v2? Upsert/deletes require v2 (report-2 unresolved-Q2); append-only is fine on v2 too. Decide with C1.
