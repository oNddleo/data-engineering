---
phase: 7
title: Acceptance Demo & Docs
status: completed
priority: P2
effort: 0.5d
dependencies:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
---

# Phase 7: Acceptance Demo & Docs

## Overview
Tie the slice into a single reproducible demo and write the docs that let someone else run
it. This is what makes it a *POC* (a thing you can show and defend), not just code.

## Requirements
- Functional: a one-command (or short scripted) path takes a clean clone to a working
  dashboard; an incremental-update demo shows deltas flowing end-to-end.
- Non-functional: a new engineer reproduces the demo in < 30 min following the README.

## Architecture
```
make demo  →  up → seed-full → dag-trigger(full) → seed-append → dag-trigger(incr) → open Superset
```
Plus a teardown (`make down` / `make reset`) returning to clean state.

## Related Code Files
- Create: `README.md` (prereqs, RAM note, quickstart, demo script, troubleshooting)
- Create: `docs/poc-architecture.md` (what was built vs full architecture; scope deltas:
  CDC deferred, Rust/Python write split, ClickHouse omitted — with rationale)
- Create: `docs/demo-runbook.md` (step-by-step demo + expected outputs/screenshots)
- Create: `Makefile` target `demo` (orchestrates the full happy path)
- Modify: `Makefile` (ensure `up/down/reset/seed-*/dag-trigger/bi-*` all present)

## Implementation Steps
1. `make demo`: scripts the full happy path (up → seed-full → full DAG run → seed-append →
   incremental DAG run → print Superset URL). Idempotent from `make reset`.
2. `README.md`: prerequisites (Docker RAM ≥14GB for full stack; ~6–7GB for MVP P1–P4),
   pinned versions, quickstart, the demo command, and a troubleshooting section seeded with
   the known gotchas (path-style S3, service DNS, bucket pre-creation, Trino S3 property
   generation, Airflow deps). Capture the real `docker stats` peak here.
3. `docs/poc-architecture.md`: map POC components onto the 7-layer reference; state
   explicitly what is in/out of scope and WHY (link plan.md). Record the honest Rust gap:
   reads/catalog/transform are Rust; Iceberg writes are PyIceberg.
4. `docs/demo-runbook.md`: the narrative for showing it — what to click, what numbers to
   expect, where incremental shows up in Iceberg snapshots.
5. Full clean-room test: `make reset` → `make demo` on a fresh checkout; time it; fix
   anything that blocks < 30 min reproduction.
6. Capture 2–3 screenshots (dashboard, Airflow DAG, Iceberg snapshot history) into docs.

## Success Criteria
- [ ] From a clean clone + `make reset`, `make demo` reaches a working dashboard unattended
      (or with documented minimal manual steps).
- [ ] Incremental demo visibly shows delta-only ingestion (Iceberg snapshot evidence).
- [ ] README reproduction verified in < 30 min by following it literally.
- [ ] `docs/poc-architecture.md` honestly states scope cuts + the Rust/Python write split.
- [ ] Whole-POC success criteria in `plan.md` all checked.

## Risk Assessment
- **"Works on my machine"** → the clean-room `make reset` + `make demo` run is mandatory,
  not optional.
- **Doc rot vs final component versions** → pin versions in README; generate the version
  list from running containers at the end.
- **Demo too long to show live** → `make demo` should complete in minutes on baseline volume;
  keep default data volumes modest.
