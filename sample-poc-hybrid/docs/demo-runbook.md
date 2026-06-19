# Demo Runbook — end-to-end on a laptop

Target: from a clean checkout to a populated Superset dashboard in **under 10 minutes** on a 16 GB laptop.

## Pre-flight

```bash
make env                              # copies .env.example → .env
make kafka-id                         # paste the UUID into .env KAFKA_CLUSTER_ID
make source-deps                      # host venv for the data generators
make test-deps                        # only if you plan to run `make test`
```

## Step-by-step (manual)

| # | Step | Command | Expected duration |
|---|------|---------|-------------------|
| 1 | Boot infra | `make up-full` | ~4–6 min (image pulls + builds) |
| 2 | Confirm health | `make ps` | instant |
| 3 | Smoke handshake | `make smoke-hybrid` | ~15 s |
| 4 | Seed OLTP dim | `make seed-oltp` | ~2 s |
| 5 | Produce IoT events | `make seed-iot RATE=100 DUR=120 &` | runs 120 s |
| 6 | Run streaming bronze | `make stream-iot-bronze` | starts detached |
| 7 | Stop streaming | `make stop-stream-iot` | ~10 s graceful |
| 8 | Upload media | `make seed-media COUNT=60` | ~15 s |
| 9 | Bronze media | `make batch-media-bronze` | ~20 s |
| 10 | Silver | `make build-silver` | ~30 s |
| 11 | Gold | `make build-gold` | ~40 s |
| 12 | Bootstrap Superset | `make superset-bootstrap` | ~30 s (first run only) |
| 13 | Validate via Trino | `make trino-validate` | ~10 s |
| 14 | Open dashboards | `make superset-ui`, `make airflow-ui` | instant |

## One-shot

```bash
make demo-hybrid                      # runs steps 1, 5/6/7, 8–13 sequentially
```

## What to look at

- **Spark UI** — http://localhost:8081 (master), worker logs via `make logs`.
- **Airflow UI** — http://localhost:8086 (admin/admin).
- **Superset UI** — http://localhost:8089 (admin/admin). Hit *SQL Lab* and pick *Trino (Delta Lakehouse)*; queries from `bi/trino_validation_queries.sql` work directly.
- **MinIO console** — http://localhost:9001 (minioadmin/minioadmin). Browse the `lakehouse/` bucket to see medallion prefixes + thumbnails.
- **Trino UI** — http://localhost:8085 (no login by default).
- **Kafka UI** (full profile) — http://localhost:8090.

## Teardown

```bash
make down-hybrid                      # keeps volumes
make clean-hybrid                     # destroys everything; full reset
```

## Reset just the warehouse (keep raw data + thumbnails)

```bash
make reset-warehouse
```

Useful after schema changes — HMS drops + MinIO `bronze/silver/gold/_checkpoints/` are wiped, but `raw-media/` and `thumbnails/` remain.
