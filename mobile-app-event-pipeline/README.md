# mobile-app-event-pipeline

**Adjust / Appsflyer-style** mobile-attribution pipeline for the VN
market — last-touch attribution with 7-day click / 24-hour
view-through windows, install-cohort retention (D1 / D7 / D30),
per-cohort LTV in VND, and two classic fraud detectors
(**click-injection** + **install-spam / device-farm**).

Pure-Python, zero deps, integer-VND throughout.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Ingests an event stream** of `CLICK`, `IMPRESSION`, `INSTALL`,
   `OPEN`, `IN_APP`, `PURCHASE` events — what Adjust / Appsflyer /
   AppMetrica emit and what VN marketplaces (Shopee, Tiki, Lazada,
   MoMo, ZaloPay) ingest.
2. **Attributes each install** to a click (7-day window) or
   impression (24-hour window), with **last-touch + click-overrides-view**
   precedence; otherwise marks it `organic`.
3. **Cohorts installs by their VN_TZ install date** and reports
   D1 / D7 / D30 retention curves (active = at least one
   `OPEN`/`IN_APP`/`PURCHASE` in that 24-hour day window).
4. **Computes LTV** per cohort cumulatively at D1, D7, D30 (revenue
   sum ÷ cohort size, integer-VND).
5. **Detects two classic fraud patterns**:
   - **Click-injection** — installs attributed with implausibly
     short lag (Adjust's 20-second threshold). A network firing
     clicks 1-15 seconds before an install almost certainly hijacked
     an organic conversion.
   - **Install-spam / device-farm** — a source with high install
     volume but D1 retention collapsed below 5% (real campaigns sit
     at 20-40%). Surfaces device-farm operators selling installs
     that never open the app.

## Event schema

| Kind         | Meaning                                                |
| ------------ | ------------------------------------------------------ |
| `CLICK`      | Ad click on a promoted source/campaign.                |
| `IMPRESSION` | Ad impression — used for view-through attribution.     |
| `INSTALL`    | App opened for the first time on this device.          |
| `OPEN`       | App opened on an already-installed device.             |
| `IN_APP`     | Custom event (`level_up`, `share`, `view_item`, …).    |
| `PURCHASE`   | Monetised in-app purchase — `revenue_vnd > 0`.         |

All money is integer VND, all timestamps are tz-aware (`VN_TZ`).
`device_id` is the cross-event join key (IDFA / GAID / AAID).

## Attribution rules

The canonical Appsflyer matching order, walked per install:

1. **Last qualifying click** within the click-window (default 7d).
2. **Last qualifying impression** within the view-window (default
   24h) — only if no click matched.
3. **Organic** — no attributable touchpoint.

Ties broken by lexicographic `event_id` for deterministic output.
View-through never overrides a click.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `mappev.schema`    | `Event`, `EventKind`, `Attribution`, `CohortRetention`, `CohortLTV`, `VN_TZ` |
| `mappev.attribute` | Last-touch attribution with 7d click / 24h view windows             |
| `mappev.cohort`    | D1 / D7 / D30 retention curves + cumulative LTV per install cohort  |
| `mappev.fraud`     | `find_click_injection` (lag-threshold) + `find_install_spam` (D1-rate) |
| `mappev.simulator` | Seeded synthetic event stream (organic + click + view + fraud mixes) |
| `mappev.io_jsonl`  | Type-checked JSONL codec for events, attributions, cohorts, frauds   |
| `mappev.cli`       | `mappev info \| simulate \| attribute \| cohort \| ltv \| fraud \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
mappev info
mappev simulate  --devices 200 --days 30 --seed 7 --output events.jsonl
mappev attribute --input events.jsonl --output attr.jsonl --show 5
mappev cohort    --input events.jsonl --show 10
mappev ltv       --input events.jsonl --show 10
mappev fraud     --input events.jsonl --min-lag-seconds 20 --min-installs 5
mappev summary   --input events.jsonl
```

Sample `attribute --show 5`:

```
device         source         campaign                    lag_s
D-00000075     tiktok         vn_branded_hashtag         158400
D-00000071     google_ads     search_competitor          388800
D-00000066     tiktok         vn_videoview               313200
D-00000069     facebook       vn_promo                   349200
D-00000034     organic                                        0
```

Sample `cohort --show 5`:

```
date           size    D1%    D7%   D30%
2026-05-01        4 100.0%  25.0%   0.0%
2026-05-03        4  50.0% 100.0%   0.0%
2026-05-04       11 100.0%  18.2%   0.0%
2026-05-05       12  75.0%  41.7%   0.0%
2026-05-06        9  77.8%  11.1%   0.0%
```

Sample `ltv --show 5`:

```
date           size     LTV_D1     LTV_D7    LTV_D30
2026-05-01        4    124,750    174,500    299,250
2026-05-03        4          0    186,500    186,500
2026-05-04       11     45,363     81,454     90,454
2026-05-05       12     33,166    145,250    145,250
2026-05-06        9      5,444    171,333    226,777
```

Sample `fraud` (exits 2 when any finding):

```
CLICK_INJECTION (1):
  dodgy_network:shady_campaign        3 installs attributed with lag < 20s (median ~ 10s)
INSTALL_SPAM (0):
```

Sample `summary`:

```json
{
  "n_events": 1047,
  "n_devices_attributed": 100,
  "events_by_kind": {
    "CLICK": 55,
    "IMPRESSION": 10,
    "INSTALL": 100,
    "IN_APP": 229,
    "OPEN": 585,
    "PURCHASE": 68
  },
  "installs_by_source": {
    "dodgy_network": 8,
    "facebook": 15,
    "google_ads": 18,
    "organic": 35,
    "spam_dsp": 2,
    "tiktok": 10,
    "zalo": 12
  },
  "n_cohorts": 14,
  "total_purchase_revenue_vnd": 16082000,
  "weighted_avg_d1_retention_pct": 81.0,
  "weighted_avg_d30_ltv_vnd": 160819.8
}
```

## Library

```python
from mappev.attribute import attribute
from mappev.cohort    import ltv, retention
from mappev.fraud     import find_click_injection, find_install_spam
from mappev.simulator import generate

events       = generate(n_devices=200, n_days=30, seed=7)
attributions = attribute(events)            # 7-day click, 24h view
cohorts      = retention(events)            # D1 / D7 / D30
ltv_rows     = ltv(events)                  # cumulative LTV per cohort
injection    = find_click_injection(attributions, min_lag_seconds=20)
spam         = find_install_spam(events, attributions, min_installs=5)
```

## Key design decisions

- **Last-touch with click-overrides-view, click-window 7 days,
  view-window 24 hours** — matches Appsflyer / Adjust defaults
  ("install referrer broadcast" attribution). Tunable per call.
- **Cohort by VN_TZ install date, not UTC** — VN marketplaces
  report install metrics in local time, and a UTC-23:30 install
  is the next day in VN. Same convention as
  `seller-performance-data-mart`.
- **Cumulative LTV, disjoint retention windows.** Revenue D1 ⊆ D7
  ⊆ D30 (cumulative is what marketers compare against payback
  curves). Retention windows are 24-hour disjoint slices (so a
  D7 row is "active on day 7", not "active by day 7").
- **Click-injection threshold 20 seconds** — Adjust's published
  threshold for the install-broadcast-intent attack. Below that,
  the click was almost certainly fired *in response* to the
  install broadcast, not the other way round.
- **Install-spam needs ≥ N installs + D1 rate < 5%** — single-digit
  install sources are too small to judge (could be noise); a real
  device-farm operator produces hundreds of installs across days
  with near-zero opens.
- **CI exit codes:** `fraud` exits **2** when any finding is
  surfaced, so CI/cron jobs can wire it as a gate.
- **Pure stdlib, integer-VND, banker's rounding** — same conventions
  as the rest of the catalogue (`healthcare-claims-processor`,
  `seller-performance-data-mart`). No float drift across multi-week
  campaign reports.

## Quality

```bash
make test       # 94 tests + 11 Hypothesis properties
make type       # mypy --strict
make lint
```

- **94 tests**, 0 failing; 11 Hypothesis properties (click within
  window always attributes, click outside window is always
  organic, impression past 24h is always organic, lag always
  non-negative, one Attribution per install, output sorted by
  (install_at, device_id), cohort sizes sum to install count,
  retention counts always in [0, cohort_size], LTV always
  cumulative (D1 ≤ D7 ≤ D30), single purchase within D1
  preserved, click-injection bucket sizes preserved).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `mappev` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
