# logistics-eta-tracker

VN-context shipment tracking pipeline for Shopee / Lazada / Tiki
fulfilment. Folds carrier webhook events onto a delivery-state
machine, predicts ETAs with empirical p50 / p90 lane stats, and
surfaces SLA breaches (OVERDUE + STUCK) for ops.

Supports the big-four VN 3PLs: **GHN**, **GHTK**, **VTP** (Viettel
Post), **VNPOST** (Vietnam Post).

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **State-folds** carrier tracking events onto each shipment's
   delivery-state machine. Events arrive out-of-order, duplicated, or
   in carrier-bug sequences — the tracker sorts by `occurred_at`,
   skips idempotent re-emits, and silently drops illegal backwards
   transitions (`DELIVERED → IN_TRANSIT` is a webhook bug we tolerate).
2. **ETA prediction** using empirical p50 / p90 transit-time per
   `(origin_district, dest_district, carrier)` lane. Three-tier
   fallback: lane → carrier-wide → global, so cold-start lanes still
   get a useful number (and the source is recorded for dashboards).
3. **SLA monitor** flags two breach kinds: `OVERDUE` (non-terminal
   shipment past its quoted `promised_at`) and `STUCK` (shipment
   hasn't transitioned in N hours). Tuneable threshold; pure function
   over `now` so tests can pin time.
4. **Carrier leaderboard** with delivered % / failure % / on-time %
   / median transit. A min-volume filter prevents a carrier with 1
   delivery and 100% on-time from out-ranking GHN's 1000 deliveries
   at 95%.

## Delivery state machine

```
       CREATED ──┐
          │      └──► FAILED (pickup failed)
          ▼
       PICKED_UP ──► IN_TRANSIT ◄──► AT_HUB
                                │       │
                                ▼       ▼
                          OUT_FOR_DELIVERY ──► DELIVERED
                                │   ▲
                                │   └── (one more try)
                                ▼
                              FAILED ──► RETURNED
```

Legal transitions are baked in as a `frozenset`; the validator also
permits idempotent re-emits (any state → same state). Anything else
is dropped and counted in `ShipmentStatus.n_dropped_events`.

## Components

| Module                 | Role                                                                  |
| ---------------------- | --------------------------------------------------------------------- |
| `logietr.schema`       | `Carrier`, `ShipmentState`, `Shipment`, `TrackingEvent`, `is_legal_transition` |
| `logietr.tracker`      | `apply_events(shipments, events) → {id: ShipmentStatus}` + `state_distribution` |
| `logietr.eta`          | `build_lane_stats` (empirical p50/p90) + `predict_eta` (3-tier fallback) |
| `logietr.sla`          | `find_overdue`, `find_stuck` — pure functions over (statuses, now)      |
| `logietr.leaderboard`  | `carrier_scorecards`, `rank_by_on_time(min_volume=10)`                  |
| `logietr.simulator`    | Seeded coherent shipments + events with per-carrier transit distributions |
| `logietr.io_jsonl`     | Type-checked JSONL codec for shipments + events                         |
| `logietr.cli`          | `logietr info \| simulate \| status \| eta \| breaches \| carriers \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
logietr info
logietr simulate  --n 300 --seed 7 --out-dir ./raw
logietr status    --in-dir ./raw
logietr eta       --in-dir ./raw --n 10
logietr breaches  --in-dir ./raw --stuck-hours 24
logietr carriers  --in-dir ./raw --min-volume 10
logietr summary   --in-dir ./raw
```

Sample `status` output:

```
state                   count
CREATED                     0
PICKED_UP                  17
IN_TRANSIT                 24
AT_HUB                     14
OUT_FOR_DELIVERY            1
DELIVERED                 236
FAILED                      0
RETURNED                    8
```

Sample `carriers` output (ranked by on-time %, min 10 deliveries):

```
carrier   total  deliv  fail  ret  on_time%  median_h
GHN          71     69     0    2    100.0%     24.1h
VTP          74     67     0    7    100.0%     30.3h
GHTK         66     61     0    5    100.0%     35.6h
VNPOST       89     86     0    3    100.0%     46.9h
```

Sample `breaches`:

```
OVERDUE (53):
  S-000000   AT_HUB             overdue 92.0h
  S-000025   IN_TRANSIT         overdue 90.9h
STUCK (56):
  S-000022   PICKED_UP          stuck   108.7h
  S-000025   IN_TRANSIT         stuck   106.4h
```

## Library

```python
from logietr.simulator   import generate
from logietr.tracker     import apply_events
from logietr.eta         import build_lane_stats, predict_eta
from logietr.sla         import find_overdue
from logietr.leaderboard import carrier_scorecards, rank_by_on_time
from logietr.schema      import ShipmentState

shipments, events = generate(n_shipments=500, seed=42)
statuses = apply_events(shipments, events)

completed = [s for s in statuses.values() if s.state is ShipmentState.DELIVERED]
lanes     = build_lane_stats(completed, min_samples=5)
pending   = [s for s in statuses.values() if not s.is_terminal]
for pred in predict_eta(pending, lanes)[:5]:
    print(pred.shipment_id, pred.source, pred.predicted_p50)

cards = carrier_scorecards(list(statuses.values()))
for c in rank_by_on_time(cards, min_volume=20):
    print(c.carrier.value, f"on-time={c.on_time_pct:.1f}%")
```

## Key design decisions

- **Illegal transitions are dropped, not raised.** Carrier webhooks
  are buggy in production — they replay events, fire late, and
  occasionally regress state. Raising on every bad event would
  hold up the entire batch; instead the tracker counts drops in
  `n_dropped_events` so ops can monitor noisy carriers.
- **Lane stats use empirical quantiles, not Gaussian fits.** VN
  logistics distributions are heavy-tailed (Tết / monsoon / weekend
  pickup gaps), so a mean-based ETA would skew by hours. Nearest-rank
  p50 / p90 is robust without assuming a distribution shape.
- **Three-tier fallback for ETA.** Lane → carrier → global. Each
  prediction records which tier it came from so dashboards can
  highlight cold-start estimates. A 48h / 96h pessimistic default
  applies only when no carrier has ever completed a shipment.
- **`now` injected, never `datetime.now()`.** The SLA monitor is a
  pure function over `(statuses, now)` — tests pin time and replay
  scenarios deterministically.
- **STUCK skips never-acknowledged shipments.** A `CREATED` shipment
  with no events isn't a carrier stuck — it's the seller failing
  to hand off the parcel. Different alerting channel; the SLA
  monitor only flags carrier-attributable delays.
- **Volume floor on rankings.** `rank_by_on_time(min_volume=10)` —
  one fluky perfect delivery doesn't out-rank 1,000 imperfect ones.

## Quality

```bash
make test       # 78 tests + 4 Hypothesis properties
make type       # mypy --strict
make lint
```

- **78 tests**, 0 failing; 4 Hypothesis properties (terminal state
  is sticky, orphan events don't mutate known shipments, idempotent
  re-emit is always legal, history is sorted by `occurred_at`).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `logietr` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
