# vnpost-tracking-event-pipeline

VN courier tracking event pipeline covering the 5 majors (Viettel
Post, GiaoHangNhanh, GiaoHangTietKiem, J&T Express, Shopee Express).
Parcel state machine (`CREATED → PICKED_UP → IN_TRANSIT → AT_HUB
→ OUT_FOR_DELIVERY → DELIVERED` plus return / lost / exception
paths), per-courier on-time SLA roll-up (**Tết-aware** transit
adjustment), scan-skipping + abnormal-dwell fraud detection, and a
bundled hub network for HCM / HN / DN / HP / CT.

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Ingests scan events** as emitted by VN courier scanner systems
   — 8 kinds: ``CREATED``, ``PICKED_UP``, ``IN_TRANSIT``,
   ``AT_HUB``, ``OUT_FOR_DELIVERY``, ``DELIVERED``,
   ``RETURN_TO_SENDER``, ``EXCEPTION``.
2. **Stitches** the per-tracking event stream into ``Parcel`` rows
   via a **state-machine validator** that rejects illegal scan
   transitions (e.g. DELIVERED followed by IN_TRANSIT).
3. **Rolls up on-time SLA** per courier against each courier's
   published target (24-36h same-city, 72-120h inter-city).
   **Tết-aware**: optionally subtracts the 5-day Tết block + the
   surrounding weekend from each parcel's transit time before
   comparing to SLA, so couriers aren't penalised for nationally-
   mandated closures.
4. **Detects two fraud / quality patterns**:
   - **Scan-skipping** — inter-city parcel delivered with < 4
     scans (no AT_HUB or IN_TRANSIT recorded). Either operational
     bug or a driver faking a delivery to clear backlog.
   - **Abnormal hub dwell** — a parcel sat at one hub for far
     longer than the population p95 + 3 × IQR.

## Courier coverage

| Courier              | Code | Same-city SLA | Inter-city SLA |
| -------------------- | ---- | ------------- | -------------- |
| Viettel Post         | VTP  | 24 h          | 120 h          |
| GiaoHangNhanh        | GHN  | 24 h          | 72 h           |
| GiaoHangTietKiem     | GHTK | 36 h          | 96 h           |
| J&T Express          | JT   | 24 h          | 96 h           |
| Shopee Express       | SPX  | 24 h          | 72 h           |

Targets calibrated against published 2024 service guides — production
callers tune via the `couriers.profile()` / `couriers.sla_hours()`
helpers.

## Hub network (bundled)

16 high-volume hubs across 5 cities:

| City | Code prefix | Hubs                                          |
| ---- | ----------- | --------------------------------------------- |
| HCM  | `HCM-*`     | TPN, Q12, BC, TD, CC (5)                      |
| HN   | `HN-*`      | CG, HD, LB, DA (4)                            |
| DN   | `DN-*`      | HC, LC (2)                                    |
| HP   | `HP-*`      | NG, AD (2)                                    |
| CT   | `CT-*`      | NK, CR (2)                                    |
| —    | `VN-NSC`    | National Sortation Center (1)                 |

`hubs.gateways()` returns the 8 inter-city sort centres.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `vnpost.schema`    | `ParcelEvent`, `Parcel`, `CourierSLA`, `CourierCode`, enums         |
| `vnpost.hubs`      | Bundled hub directory + gateway flags                                |
| `vnpost.couriers`  | Courier directory + per-courier SLA targets                          |
| `vnpost.state`     | State-machine validator + `stitch()` event → Parcel                  |
| `vnpost.sla`       | On-time SLA computation, Tết-aware transit adjustment                |
| `vnpost.fraud`     | `find_scan_skipping`, `find_abnormal_dwell`                          |
| `vnpost.simulator` | Seeded synthetic event stream with 6 outcome types                   |
| `vnpost.io_jsonl`  | Type-checked JSONL codec                                             |
| `vnpost.cli`       | `vnpost info \| simulate \| stitch \| sla \| fraud \| summary`      |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vnpost info
vnpost simulate --parcels 500 --seed 7 --output events.jsonl
vnpost stitch   --input events.jsonl --output parcels.jsonl --show 5
vnpost sla      --input events.jsonl
vnpost sla      --input events.jsonl --no-tet-aware
vnpost fraud    --input events.jsonl --show 5
vnpost summary  --input events.jsonl
```

Sample `stitch --show 5`:

```
tracking       courier status     origin     dest       evts
T-00000017     JT      DELIVERED  HP-NG      CT-NK         7
T-00000160     GHN     DELIVERED  HP-AD      HCM-Q12       7
T-00000013     VTP     DELIVERED  HP-NG      DN-HC         7
T-00000025     VTP     DELIVERED  CT-CR      HN-DA         7
T-00000037     GHTK    DELIVERED  CT-NK      HCM-BC        7
```

Sample `sla`:

```
courier  parcels  delivered  on-time%  p95_h  med_h
GHN         100         91     91.2%    74h    56h
GHTK         89         83     83.3%   131h    76h
JT          101         94     85.4%   166h    76h
SPX         102         96     83.8%   119h    60h
VTP         108         97     85.0%   152h    94h
```

Sample `fraud` (exits **2** when any finding):

```
SCAN_SKIPPING (13):
  GHTK T-00000050     only 3 scans for HCM→DN (need ≥4)
  GHTK T-00000264     only 3 scans for HCM→HN (need ≥4)
  GHTK T-00000322     only 3 scans for CT→HCM (need ≥4)
ABNORMAL_DWELL (20):
  GHN  T-00000236     dwell 167h at CT-NK (threshold 68h, p95 23h)
  SPX  T-00000446     dwell 158h at HN-HD (threshold 68h, p95 23h)
  GHN  T-00000166     dwell 152h at HCM-TPN (threshold 68h, p95 23h)
```

Sample `summary`:

```json
{
  "n_events": 3325,
  "n_parcels": 500,
  "by_status": {
    "DELIVERED": 461, "EXCEPTION": 16, "RETURNED": 23
  },
  "by_courier": {
    "GHN": 100, "GHTK": 89, "JT": 101, "SPX": 102, "VTP": 108
  },
  "avg_on_time_rate_pct": 86.3,
  "n_scan_skip_findings": 13,
  "n_abnormal_dwell_findings": 20
}
```

## Library

```python
from vnpost.fraud     import find_abnormal_dwell, find_scan_skipping
from vnpost.simulator import generate
from vnpost.sla       import compute_sla
from vnpost.state     import stitch

events  = generate(n_parcels=500, seed=7)
parcels = stitch(events)             # state-machine-validated rows
slas    = compute_sla(parcels)       # per-courier on-time roll-up (Tết-aware)
skip    = find_scan_skipping(parcels)
dwell   = find_abnormal_dwell(events)

for sla in slas:
    print(f"{sla.courier.value}: {sla.on_time_rate_pct:.1f}% on time")
```

## Key design decisions

- **State machine is permissive about same-city.** `PICKED_UP →
  OUT_FOR_DELIVERY` (no AT_HUB scan) is legal — a single driver in
  HCM Quận 1 picking up at one address and delivering to another
  doesn't need a hub leg. The fraud detector flags whether this
  shortened scan pattern is suspicious based on origin/dest city.
- **Tết-aware SLA.** During the 5-day Tết block + surrounding
  weekend, hub throughput drops to near-zero. Counting those hours
  against a courier's SLA would unfairly penalise. `tet_aware=True`
  (default) subtracts the Tết overlap from transit time before
  comparing to the SLA target. Block dates hard-coded from TCTK
  calendar for 2024-2027.
- **Scan-skipping needs different thresholds for same- vs
  inter-city.** A same-city parcel can legitimately have 3 scans
  (PICKED_UP → OUT_FOR_DELIVERY → DELIVERED). An inter-city parcel
  with 3 scans skipped the entire hub transit chain and is the
  classic "fake delivery" pattern.
- **Abnormal-dwell uses population-based threshold.** Hard-coded
  hour limits would penalise courier-specific operational patterns
  (e.g. VTP routinely uses VN-NSC; same-day in HCM uses Q12). Instead,
  we compute p95 + 3 × IQR across the actual scan-stream — adapts
  to whatever throughput the population sees.
- **Pure stdlib.** Datetime + dataclasses + enum + json — drops into
  any pipeline (Airflow, Dagster, Flink Python) without adding deps.
- **CI exit codes:** `vnpost fraud` exits **2** when any finding
  is surfaced — suitable for ops-gate cron jobs.

## Quality

```bash
make test       # 84 tests + 7 Hypothesis properties
make type       # mypy --strict
make lint
```

- **84 tests**, 0 failing; 7 Hypothesis properties (simulator
  output always stitches; parcels sorted by creation time;
  delivered parcels always have pickup time; SLA accounting
  `on_time ≤ delivered ≤ parcels`; scan-skip findings are always
  delivered inter-city parcels with < 4 events; event count
  matches `n_events`; sequences are chronological).
- mypy `--strict` clean over 10 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vnpost` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
