# vn-ride-hailing-trip-pipeline

End-to-end **Vietnamese ride-hailing pipeline** — 4-operator directory
(Grab, Be, Xanh SM, Maxim), 6-city table, trip state machine, surge
pricing, per-driver daily settlement with commission split, and three
fraud signals (ghost rides, cancellation abuse, surge gaming).

Pure Python 3.10+, zero runtime dependencies (stdlib only), 145 tests
including Hypothesis property tests, `mypy --strict` clean.

## What's in the box

| Module                  | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| `vnride.schema`         | `Trip`, `TripState`, `ServiceType`, `FareBreakdown`, `DriverSettlement` |
| `vnride.operators`      | 4 commission-based operators + 6 VN cities       |
| `vnride.pricing`        | Base + per-km + per-min + booking × surge tariff |
| `vnride.state_machine`  | Trip lifecycle transitions + validation          |
| `vnride.settlement`     | Daily driver rollup + cash-collected accounting  |
| `vnride.fraud`          | Ghost ride / cancel abuse / surge gaming         |
| `vnride.simulator`      | Deterministic seeded trip stream                 |
| `vnride.io_jsonl`       | JSONL codec for every record type                |
| `vnride.cli`            | `info | operators | cities | quote | simulate | settle | fraud | summary` |

## Quick start

```bash
# List operators and cities
python -m vnride.cli operators
python -m vnride.cli cities

# Quote a hypothetical CAR trip with 1.4× surge
python -m vnride.cli quote --service CAR --km 8.5 --minutes 22 --surge-bps 14000

# Simulate a month, then settle + detect fraud
python -m vnride.cli simulate --riders 100 --drivers 30 --days 30 \
  --seed 11 --output trips.jsonl
python -m vnride.cli settle --input trips.jsonl --output settlements.jsonl --show 5
python -m vnride.cli fraud --input trips.jsonl --show 5
python -m vnride.cli summary --input trips.jsonl
```

## VN ride-hailing operators (2026)

Gojek shut down VN operations on 2024-09-16, leaving four active
commission-based platforms:

| Abbr   | Name                                      | CAR%  | BIKE% | Share |
| ------ | ----------------------------------------- | ----- | ----- | ----- |
| GRAB   | Grab Vietnam                              | 25.0  | 20.0  | 68.0% |
| BE     | Be Group                                  | 20.0  | 15.0  | 24.0% |
| XANHSM | Xanh SM (Green and Smart Mobility)        | 15.0  | 12.0  |  6.0% |
| MAXIM  | Maxim Vietnam                             | 15.0  | 10.0  |  2.0% |

Xanh SM also operates a salaried-fleet model alongside cooperative
drivers; we model only the cooperative-driver flow (the salaried fleet
doesn't appear in commission settlements).

## VN cities

6 tier-1 / tier-2 cities by population, each with a city-default
peak-surge multiplier:

| Code | City             | Pop (k) | Peak surge |
| ---- | ---------------- | ------- | ---------- |
| SGN  | Ho Chi Minh City | 9 000   | 1.40×      |
| HAN  | Hanoi            | 8 500   | 1.35×      |
| HPH  | Hai Phong        | 2 100   | 1.20×      |
| DAD  | Da Nang          | 1 300   | 1.20×      |
| CTH  | Can Tho          | 1 250   | 1.15×      |
| NHA  | Nha Trang        |   550   | 1.15×      |

## Pricing

Default tariff (VND) — all components multiplied by surge except
booking fee:

| Service  | Base   | Per km  | Per min | Booking | Minimum |
| -------- | ------ | ------- | ------- | ------- | ------- |
| CAR      | 15 000 | 12 000  | 400     | 3 000   | 25 000  |
| BIKE     |  8 000 |  4 500  | 200     | 2 000   | 12 000  |
| DELIVERY | 10 000 |  5 500  | 300     | 2 500   | 15 000  |

Surge is bounded to ``[1.0×, 3.0×]`` per Bộ Công Thương soft-cap;
expressed as basis points (10 000 = 1.0×) for integer-VND math
without float drift.

## Trip state machine

```
                  +-------> NO_DRIVER     (system failed to match)
                  |
    REQUESTED --> ASSIGNED --> ARRIVING --> PICKED_UP --> COMPLETED
        |             |             |             |
        +-------------+-------------+-------------+-----> CANCELLED
```

``validate_transition(old, new)`` raises on illegal hops;
``validate_history(states)`` validates a full event log.

## AML / fraud detection

* **Ghost ride** — COMPLETED trip with distance < 100 m AND duration
  < 30 s. Driver/rider promo collusion pattern.
* **Cancellation abuse** — driver with ≥ 20 trips and a cancellation
  rate ≥ 50%.
* **Surge gaming** — (rider, driver) pair sharing ≥ 5 trips, every
  one of which was in a surge window. Off-platform coordination.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 10 source files clean
pytest                        # 145 tests, all green
```

## License

MIT
