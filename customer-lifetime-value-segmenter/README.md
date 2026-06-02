# customer-lifetime-value-segmenter

Classic CRM analytics for VN-marketplace buyers: RFM (Recency /
Frequency / Monetary) scoring → 10 named segments (Champions, Loyal,
At Risk, Hibernating, …) → per-customer CLV forecast → segment-
transition analysis. The mapping table follows what Shopee / Lazada
CRM teams actually run.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates** `Customer` and `Order` records at the boundary —
   tz-aware datetimes, positive amounts, non-empty IDs.
2. **Aggregates** orders per customer into raw `(recency_days,
   frequency, monetary_vnd)` values relative to a caller-supplied
   `as_of` timestamp.
3. **Quintile-scores** each dimension across the customer population:
   R is inverted (recent = high), F and M direct. Never-bought
   customers are short-circuited to `F=1, M=1` (the LOST corner).
4. **Maps** the (R, F, M) triple to one of 10 named segments via a
   pure function — composable with the scoring engine and the
   transition tracker.
5. **Forecasts CLV** as `AOV × frequency × expected_lifetime / window`,
   using a per-segment lifetime lookup (CHAMPIONS get 3 years,
   LOST get 0 days).
6. **Tracks transitions** (`before → after`) for cohort-movement
   dashboards (e.g. "this week 47 customers fell from LOYAL into
   AT_RISK").

## Segment mapping

The standard one used by major VN-marketplace CRM teams. `m_score`
is intentionally **not** part of the segment selector — it's used
for ranking *within* a segment, not for picking the segment:

| R   | F   | Segment              | Action                          |
| --- | --- | -------------------- | ------------------------------- |
| 5   | 5   | CHAMPIONS            | reward, upsell, ask for review  |
| 4-5 | 3-4 | LOYAL_CUSTOMERS      | retention campaign              |
| 5   | 1-2 | NEW_CUSTOMERS        | welcome flow, 2nd-order push    |
| 3-4 | 4-5 | POTENTIAL_LOYALISTS  | nurture                         |
| 3   | 1-3 | NEED_ATTENTION       | reactivation offer              |
| 2-3 | 2-3 | ABOUT_TO_SLEEP       | win-back coupon                 |
| 1-2 | 4-5 | AT_RISK              | high-value reactivation         |
| 1   | 5   | CANT_LOSE_THEM       | escalation: CS phone outreach   |
| 1-2 | 2-3 | HIBERNATING          | low-cost email blast            |
| 1   | 1   | LOST                 | suppress / re-acquisition only  |

## Components

| Module                | Role                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `clvseg.schema`       | `Customer`, `Order`, `RFMScore`, `Segment` enum, `VN_TZ`              |
| `clvseg.rfm`          | `score(customers, orders, as_of) → list[RFMScore]`                    |
| `clvseg.segments`     | `rfm_to_segment`, `classify_all`, `segment_distribution`, `top_in_segment`, `transitions` |
| `clvseg.clv`          | `forecast`, `top_clv`, `total_clv_by_segment` — segment-aware lifetime |
| `clvseg.simulator`    | Seeded synthetic customer + order streams across 9 archetypes          |
| `clvseg.io_jsonl`     | Type-checked JSONL codec for all four record types                     |
| `clvseg.cli`          | `clvseg info \| simulate \| score \| segment \| clv \| top \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
clvseg info
clvseg simulate --customers 500 --window-days 180 --seed 7 --out-dir ./raw
clvseg score    --in-dir ./raw --output ./scores.jsonl
clvseg segment  --scores ./scores.jsonl
clvseg clv      --scores ./scores.jsonl --window-days 180 --show-top 10
clvseg top      --scores ./scores.jsonl --segment CHAMPIONS --n 10
clvseg summary  --scores ./scores.jsonl
```

Sample `segment` output:

```
segment                  count     pct
CHAMPIONS                   62   12.4%
LOYAL_CUSTOMERS            138   27.6%
POTENTIAL_LOYALISTS         71   14.2%
HIBERNATING                100   20.0%
ABOUT_TO_SLEEP              73   14.6%
```

Sample `clv --show-top` output:

```
customer   segment                       aov  freq        forecast
C-000068   CHAMPIONS               2,007,501    13     158,759,870
C-000434   CHAMPIONS               2,299,246    11     153,857,878
C-000098   CHAMPIONS               1,917,467    13     151,639,681
```

Sample `clv` rollup:

```
segment                       total_clv_vnd
CHAMPIONS                     4,263,949,099
LOYAL_CUSTOMERS               1,051,620,732
POTENTIAL_LOYALISTS             233,292,459
```

## Library

```python
from clvseg.simulator import generate
from clvseg.rfm       import score
from clvseg.segments  import classify_all, transitions
from clvseg.clv       import forecast, top_clv

customers, orders, as_of = generate(n_customers=500, window_days=180, seed=42)
scores       = score(customers, orders, as_of)
assignments  = classify_all(scores)
forecasts    = forecast(scores, assignments, window_days=180)

for f in top_clv(forecasts, n=10):
    print(f.customer_id, f.segment.value, f.forecast_vnd)

# Week-over-week movement
prev_scores      = score(customers, orders_last_week, as_of - timedelta(days=7))
prev_assignments = classify_all(prev_scores)
moves            = transitions(prev_assignments, assignments)
for (before, after), n in sorted(moves.items(), key=lambda kv: -kv[1])[:10]:
    print(f"{before.value} → {after.value}: {n}")
```

## Key design decisions

- **Integer VND** throughout. No `Decimal`, no `float` drift.
  Consistent with every other repo in this catalogue
  (`seller-performance-data-mart`, `shopee-product-scraper-warehouse`,
  `review-sentiment-vietnamese`).
- **Population-relative quintiles**, not absolute cutoffs. A
  "frequency = 3" customer in a base of high-frequency buyers gets
  F=1; the same customer in a low-frequency base gets F=5. That's
  the correct CRM semantic — segment membership is *relative* to
  the cohort being analysed, not absolute.
- **Never-bought short-circuit**. A customer with zero in-window
  orders gets `F=1, M=1` directly, bypassing quintile scoring. In a
  small population of only never-bought customers (a degenerate
  edge case), quintile scoring would otherwise put them in F=5
  — which is the wrong CRM action.
- **`m_score` is computed but not used by `rfm_to_segment`.** That
  mirrors industry practice: M is used for ranking *within* a
  segment (which CHAMPIONS to give the upsell to), not for picking
  the segment itself.
- **Pure `transitions` function**. Customers in only one snapshot
  (new acquisitions / churn) are skipped — those belong on a
  separate dashboard. The function only counts actual movement.
- **Segment-aware CLV lifetime**. A CHAMPION's expected lifetime
  (3 years) is materially different from an AT_RISK customer's
  (4 months). Using a flat lifetime hides the retention spread that
  drives marketing budget allocation.

## Quality

```bash
make test       # 79 tests + 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **79 tests**, 0 failing; 5 Hypothesis properties (RFM-to-segment
  mapping is total over the 125-cell RFM cube, R=5/F=5 is always
  CHAMPIONS, R=1/F=1 is always LOST, CLV forecast is always ≥ 0,
  `expected_lifetime_days` always matches the segment lookup).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `clvseg` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
