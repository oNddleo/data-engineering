# ride-share-trip-pipeline

**Grab / Gojek / Be**-style ride-hailing trip pipeline for the VN
market — trip state machine (REQUEST → ACCEPT → PICKUP → DROPOFF
or CANCEL/EXPIRE), fare calculation matching published VN consumer
rates, ETA accuracy, surge-window detection per district × hour,
per-driver utilization shifts, and two classic fraud detectors
(**cancel-abuse** + **phantom-trip**).

Pure-Python, zero deps, integer-VND throughout.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Ingests trip events** — seven kinds (`REQUEST`, `ACCEPT`,
   `PICKUP`, `DROPOFF`, `CANCEL`, `EXPIRE`, `SURGE_UPDATE`) — what
   Grab / Gojek / Be back-ends emit on the dispatch and trip
   channels.
2. **Stitches** the unordered event stream into one `Trip` per
   `trip_id` while validating the state machine (rejects DROPOFF
   without prior PICKUP, post-terminal events, etc).
3. **Computes the fare breakdown** per completed trip: base +
   distance (over the 2-km included) + time + surge multiplier,
   matching published VN rates as of May 2026 (see Rate card).
4. **Detects surge windows** — district × hour-of-VN-day buckets
   where average surge ≥ 1.2× *and* completion rate < 50%. These
   are the markets where supply needs reinforcement.
5. **Computes per-driver utilization shifts** — for each
   `(driver, shift_date)`, online-time, on-trip-time, completed
   trips, revenue. Healthy drivers sit at 50-70% utilization;
   < 30% suggests under-dispatched.
6. **Surfaces two classic fraud patterns**:
   - **Cancel-abuse** — drivers with cancel-rate ≥ 30% AND median
     accept-to-cancel lag ≤ 30 seconds. Signals the "accept-to-hold-
     queue-then-cancel" attack.
   - **Phantom-trip** — drivers with completed trips where
     `distance_m < 200` OR `ride_seconds < 30`. Used to inflate
     trip-count incentives.

## Trip state machine

```
                          ACCEPT       PICKUP        DROPOFF
       REQUEST ────────────► ACCEPTED ────► PICKED ────► COMPLETED
          │                     │              │
          │ EXPIRE (5min)       │ CANCEL       │ CANCEL
          ↓                     ↓              ↓
       EXPIRED              CANCELLED      CANCELLED
```

`stitch()` validates this per-trip event sequence; illegal
transitions (e.g. DROPOFF without PICKUP, ACCEPT after CANCEL) raise
`ValueError`.

## Rate card (published Grab VN rates, May 2026)

| Vehicle    | Base       | First km included | VND/km    | VND/min |
| ---------- | ---------- | ----------------- | --------- | ------- |
| MOTORBIKE  | 12,000     | 2 km              | 4,000     | 200     |
| CAR_4      | 25,000     | 2 km              | 11,000    | 400     |
| CAR_7      | 30,000     | 2 km              | 13,000    | 500     |
| DELIVERY   | 15,000     | 2 km              | 5,000     | 0       |

Surge multiplier in basis points (`10_000 bps = 1.0×`). All
computation is integer-VND with **banker's rounding** (round-
half-to-even) — same convention as `healthcare-claims-processor`
and `vn-tax-invoice-validator`.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `vntrip.schema`    | `TripEvent`, `TripEventKind`, `CancelBy`, `VehicleClass`, `Trip`, `FareBreakdown`, `SurgeWindow`, `DriverShift`, `VN_TZ` |
| `vntrip.districts` | VN district directory (HCM × 10, HN × 7, DN × 3) with vi/en names    |
| `vntrip.state`     | State-machine validator + `stitch()` event→Trip view                |
| `vntrip.fare`      | `compute_fare()` with VN rate card + banker's rounding              |
| `vntrip.analytics` | ETA-accuracy ratios + percentiles, surge-window detection, driver shifts |
| `vntrip.fraud`     | `find_cancel_abuse()` + `find_phantom_trips()` detectors            |
| `vntrip.simulator` | Seeded synthetic stream with 6 outcome types + fraud injection      |
| `vntrip.io_jsonl`  | Type-checked JSONL codec for all record types                       |
| `vntrip.cli`       | `vntrip info \| simulate \| stitch \| fare \| surge \| shifts \| fraud \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vntrip info
vntrip simulate --riders 100 --drivers 25 --days 7 --seed 7 --output events.jsonl
vntrip stitch   --input events.jsonl --output trips.jsonl --show 5
vntrip fare     --input events.jsonl --output fares.jsonl --show 5
vntrip surge    --input events.jsonl --show 10
vntrip shifts   --input events.jsonl --show 10
vntrip fraud    --input events.jsonl --min-accepts 10 --max-cancel-rate-pct 30
vntrip summary  --input events.jsonl
```

Sample `stitch --show 5`:

```
trip           rider    driver   status      dist_m       fare
T-00000099     R-00054  D-00024  CANCEL           0          0
T-00000137     R-00075  D-00017  DONE          6318     83,451
T-00000154     R-00086  D-00020  DONE          4447     24,741
T-00000118     R-00065  D-00013  DONE          8989     45,713
T-00000157     R-00087  D-00003  DONE         13679    175,312
```

Sample `fare --show 5`:

```
trip               base     dist    time  surge×      total
T-00000137       25,000   47,498  10,953   1.00×     83,451
T-00000154       12,000    9,788   2,953   1.00×     24,741
T-00000118       12,000   27,956   5,757   1.00×     45,713
T-00000157       25,000  128,469   5,906   1.10×    175,312
T-00000128       25,000  119,372   4,480   1.00×    148,852
```

Sample `shifts --show 5`:

```
driver     date          trips    rev_vnd  online_h  util%
D-00000    2026-05-01        8    504,676     15.7h  17.8%
D-00001    2026-05-01        9    656,514     16.0h  25.1%
D-00002    2026-05-01        5    552,314      9.6h  21.1%
D-00003    2026-05-01        6    416,011     11.2h  19.1%
D-00004    2026-05-01        4    268,998      8.4h  19.7%
```

Sample `fraud` (exits 2 when any finding):

```
CANCEL_ABUSE (1):
  D-00000    cancelled 30/71 accepts (42.3%), median lag 13s
PHANTOM_TRIP (14):
  D-00011    4 completions with distance<200m or duration<30s
  D-00014    4 completions with distance<200m or duration<30s
  D-00010    3 completions with distance<200m or duration<30s
```

Sample `summary`:

```json
{
  "n_events": 4272,
  "n_trips": 1186,
  "n_completed": 868,
  "n_cancelled": 318,
  "completion_rate_pct": 73.2,
  "events_by_kind": {
    "ACCEPT": 1032, "CANCEL": 258, "DROPOFF": 868,
    "EXPIRE": 60, "PICKUP": 868, "REQUEST": 1186
  },
  "total_revenue_vnd": 64910178,
  "n_driver_shifts": 175,
  "n_surge_windows_active": 50,
  "avg_driver_utilization_pct": 19.4
}
```

## Library

```python
from vntrip.analytics import driver_shifts, surge_windows
from vntrip.fare      import compute_fare
from vntrip.fraud     import find_cancel_abuse, find_phantom_trips
from vntrip.simulator import generate
from vntrip.state     import stitch

events  = generate(n_riders=100, n_drivers=25, n_days=7, seed=7)
trips   = stitch(events)
shifts  = driver_shifts(trips)
surges  = surge_windows(events)
abuse   = find_cancel_abuse(trips, min_accepts=10)
phantom = find_phantom_trips(trips, min_distance_m=200)

for trip in trips:
    if trip.is_completed:
        fare = compute_fare(
            trip_id=trip.trip_id,
            vehicle_class=trip.vehicle_class,
            distance_m=trip.distance_m,
            ride_seconds=trip.ride_seconds,
            surge_bps=trip.surge_bps,
        )
        print(trip.trip_id, fare.total_fare_vnd)
```

## Key design decisions

- **Trip stitching is event-driven, not snapshot-driven** — the
  state machine validator catches illegal transitions (e.g. DROPOFF
  without PICKUP) at stitch time rather than at write time. Matches
  how real ride-hailing systems work (events are emitted from
  multiple services; the join happens downstream).
- **Cohort by VN_TZ shift date, not UTC** — a driver in HCM finishing
  at 23:00 VN-time appears on the right calendar day; UTC would
  shift them backward by ~7 hours. Same convention as
  `seller-performance-data-mart` and `mobile-app-event-pipeline`.
- **Surge ≥ 1.2× AND completion < 50%** — a surge window is "hot"
  only when both signals fire. Surge alone (peak rush hour) doesn't
  signal a problem; collapsed completion alone might be supply
  outage. The intersection is where dispatch wants to flood
  incentives.
- **Cancel-abuse needs BOTH high cancel-rate AND short lag** — a
  driver thoughtfully cancelling on a rider mismatch (lag > 30s)
  is not abuse. A driver auto-cancelling under 30 seconds at high
  rate is.
- **Phantom-trip threshold 200m / 30s** — shorter than walking
  distance and shorter than getting in/out of the vehicle. Real
  Grab/Gojek/Be claims systems flag at similar thresholds.
- **Integer VND, banker's rounding** — eliminates float drift over
  multi-week aggregation. Same convention across the catalogue.
- **CI exit codes:** `fraud` exits **2** when any finding is
  surfaced; suitable for cron/Airflow as a gate task.

## Quality

```bash
make test       # 110 tests + 7 Hypothesis properties
make type       # mypy --strict
make lint
```

- **110 tests**, 0 failing; 7 Hypothesis properties (fare components
  always non-negative; higher surge → higher total; surge=1.0× →
  pre==total; well-formed completed sequence always stitches;
  simulator output always stitches cleanly; stitched trips always
  sorted by (requested_at, trip_id); completed trip always has
  non-empty driver_id and positive fare/distance).
- mypy `--strict` clean over 10 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vntrip` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
