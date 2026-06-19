# Troubleshooting

First-run gotchas distilled from the Phase 1, 3, and 4–6 code reviews.

## Boot

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `kafka` keeps restarting | `KAFKA_CLUSTER_ID` still the sample placeholder | `make kafka-id`, paste into `.env`, `make clean-hybrid && make up-hybrid` |
| `unity-catalog` unhealthy (only `up-uc`) | UC OSS bind-mount path wrong | Confirm UC binary location with `docker run --rm --entrypoint sh unitycatalog/unitycatalog:0.3.0 -c "ls /home/unitycatalog/bin"` |
| `trino` won't start | Catalog file syntax error | `docker compose logs trino` — look for `IllegalArgumentException`. `delta.metastore=thrift` only — `unity` is not supported by Trino 470 OSS |
| `hive-metastore` boot loop | Postgres `metastore` DB not created | `make psql-meta` then `SELECT datname FROM pg_database;` — should list metastore, ucatalog, airflow, superset |
| `airflow-init` exits 1 | Postgres airflow DB missing | Same as above; check `init-meta.sql` ran |

## Pipeline

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `make smoke-hybrid` fails with `AnalysisException: not a Delta table` | HMS still knows about a table whose Delta files were wiped | `make reset-warehouse` |
| Streaming job exits immediately | Kafka topic missing | `make kafka-topics` — `iot.sensors` should exist. If not, restart the `kafka-init` one-shot: `docker compose run --rm kafka-init` |
| `make seed-iot` blocks at startup | Broker not yet reachable on host port | Increase `--bootstrap` `9092` connect retries; check `docker compose ps kafka` is healthy first |
| Bronze media job runs but writes 0 rows | Same-second re-upload — etag collision | Wait 1 s or re-upload with a different filename; the etag is `modtime + length`, so identical content+timestamp dedups (review C2 from Phase 4) |
| Silver outlier rate doesn't match the 1% seeded | Outliers computed per-batch — see `decisions/poc-statistical-caveats` discussion in plan.md | Run with `RATE=200 DUR=600` to make per-batch stats stable |
| Trino `SELECT count(*)` returns 0 after pipeline | Schema in HMS but tables under a different catalog | `SHOW CATALOGS` and `SHOW SCHEMAS FROM delta` first; default catalog is `delta` |
| Superset can't query Trino | `trino[sqlalchemy]` dialect missing | Rebuild image: `docker compose build --no-cache superset` — `infra/superset/Dockerfile` is the source of truth |

## Stack hygiene

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Docker OOM during build | Spark image install pulls many JARs | Raise Docker Desktop memory to ≥14 GB; defer Superset (`make up-hybrid` first, then `make up-bi`) |
| `make down-hybrid` then `make up-hybrid` leaves stale Delta paths | Volumes are NOT removed by `down` | Run `make clean-hybrid` (DESTRUCTIVE) or just `make reset-warehouse` for medallion-only reset |
| Tests fail with `Java not found` | Host has no JDK | Install JDK 17 (`apt install openjdk-17-jdk-headless`) or run tests inside the Spark container |
| Tests pass locally but fail in CI | Slow tests not marked | Check `pytest.ini` — slow tests should carry `@pytest.mark.slow`; CI must opt-in via `pytest -m slow` |

## When to escalate

- Code-review reports in `plans/reports/` flagged most boot-time and silent-corruption traps; consult them for context if you hit something not listed here.
- For HMS↔MinIO desync, look at the `reset-warehouse` Makefile target — it's the canonical recovery procedure documented in Validation Session 2.
