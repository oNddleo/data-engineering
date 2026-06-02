# seller-performance-data-mart

Star-schema data mart for VN-marketplace (Shopee / Lazada / Tiki)
seller performance. Three source streams (orders, returns, reviews)
roll into one `FactSellerDay` per `(seller_id, date_key)` — with
KPI views (GMV, AOV, return rate, NPS proxy) on top.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. Validates upstream `Order`, `Return`, `Review` records at the boundary —
   tz-aware timestamps, positive money, non-empty IDs.
2. Buckets each record by **`(seller_id, day-in-VN_TZ)`**. UTC orders
   that crossed midnight in VN time are credited to the *VN* day,
   not the UTC day — the recurring bug in non-VN-aware marts.
3. Joins returns to orders via `order_id` and credits each return to
   the **originating order's day**, not the day the return was
   processed. Reviews bucket on their *own* day (filed days later, so
   they show up on the review day, matching Shopee Seller Center).
4. Materialises one `FactSellerDay` per non-empty bucket. The mart is
   sparse — a seller with zero orders on a given day has no row.
5. Exposes KPI views: per-seller summary, daily trend, top-by-GMV
   leaderboard, worst-by-return-rate offenders (with a min-orders
   floor so 1-order shops with 100% returns don't swamp the list).

## Star schema

```
  ┌─────────────┐       ┌────────────────────┐       ┌─────────────┐
  │ DimSeller   │←──────│ FactSellerDay      │──────→│ DimDate     │
  │ seller_id PK│       │ (seller_id,        │       │ date_key PK │
  │ name        │       │  date_key) PK      │       │ weekday     │
  │ onboarded_at│       │ n_orders, n_units  │       │ iso_week    │
  │ is_official │       │ gmv_vnd, refund_vnd│       │ iso_year    │
  └─────────────┘       │ n_returns, n_reviews│      └─────────────┘
                        │ sum_rating_x100    │
                        │ n_unique_buyers    │
                        └────────────────────┘
                                  │
                                  ↓
                          ┌──────────────┐
                          │ DimCategory  │  (joined via order.category_key)
                          │ category_key │
                          └──────────────┘
```

## Components

| Module                | Role                                                              |
| --------------------- | ----------------------------------------------------------------- |
| `sellermart.schema`   | `DimSeller`, `DimDate`, `DimCategory`, `FactSellerDay`, `VN_TZ`   |
| `sellermart.sources`  | `Order`, `Return`, `Review` — upstream record validation          |
| `sellermart.etl`      | `build_fact_seller_day(orders, returns, reviews)`                 |
| `sellermart.kpis`     | `seller_summary`, `daily_trend`, `top_sellers_by_gmv`, `worst_sellers_by_return_rate` |
| `sellermart.simulator`| Seeded synthetic source streams                                   |
| `sellermart.io_jsonl` | Type-checked JSONL codec for sources + facts                      |
| `sellermart.cli`      | `sellermart info \| simulate \| build \| top \| worst \| trend \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
sellermart info
sellermart simulate --days 14 --sellers 12 --seed 7 --out-dir ./raw
sellermart build    --in-dir ./raw --output ./facts.jsonl
sellermart top      --facts ./facts.jsonl --n 5
sellermart worst    --facts ./facts.jsonl --n 5 --min-orders 10
sellermart trend    --facts ./facts.jsonl
sellermart summary  --facts ./facts.jsonl
```

Sample `top` output:

```
  seller  days  orders       gmv_vnd        aov   ret%   avg★
  100000    15     227   145,270,000    639,955   7.0%   4.28
  100005    15      59    42,503,000    720,389   8.5%   4.37
  100001    15      76    41,055,000    540,197   9.2%   4.14
```

Sample `worst` output (filtered to sellers with ≥ 10 orders):

```
  seller  orders  returns    ret%    refund_vnd  refund%
  100002      62        9   14.5%     4,527,500    13.2%
  100003      53        6   11.3%     2,143,500     7.4%
```

## Library

```python
from sellermart.etl    import build_fact_seller_day
from sellermart.kpis   import seller_summary, top_sellers_by_gmv
from sellermart.simulator import generate

orders, returns, reviews = generate(n_days=30, n_sellers=20, seed=42)
facts = build_fact_seller_day(orders, returns, reviews)

summaries = seller_summary(facts)
for s in top_sellers_by_gmv(summaries, n=10):
    print(s.seller_id, s.gmv_vnd, f"{s.return_rate_pct:.1f}%",
          f"nps={s.nps_proxy:.0f}")
```

## Key design decisions

- **VN_TZ-aware bucketing.** The day-key comes from
  `created_at.astimezone(VN_TZ).date()`, so a UTC 23:30 order is
  credited to the next VN day. Tests cover the boundary explicitly.
- **Returns credited to the order's day, not the return's day.** Ops
  wants daily-cohort retention metrics, which require seeing the
  refund against the cohort it belongs to.
- **Reviews bucket on their own day.** Reviews trickle in days after
  the order; surfacing them on the review day matches the way ops
  monitors NPS in real time.
- **Sparse mart.** A seller with no orders on a day has no fact row.
  Downstream callers join on `LEFT JOIN dim_date` if they want a
  dense calendar.
- **Integer VND, integer rating × 100.** No Decimal, no float drift.
  Matches [`shopee-product-scraper-warehouse`](../shopee-product-scraper-warehouse/)
  so the two repos share keys without lossy conversion.
- **Schema-level invariants.** `FactSellerDay` rejects `n_returns >
  n_orders`, `n_units < n_orders`, `n_unique_buyers > n_orders` at
  construction time — so a bad ETL can't silently materialise garbage.

## Quality

```bash
make test       # 82 tests + 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **82 tests**, 0 failing; 5 Hypothesis properties (total-orders
  preserved, GMV preserved, unique-buyers bounded by orders, output
  sorted by `(seller_id, date_key)`, orphan returns dropped).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `sellermart` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
