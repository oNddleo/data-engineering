# Changelog

## [0.1.0] — 2026-05-15

### Added
- `DimSeller`, `DimDate`, `DimCategory`, `FactSellerDay` —
  frozen-slots dataclasses with validation at construction
  (`n_returns ≤ n_orders`, `n_units ≥ n_orders`,
  `n_unique_buyers ≤ n_orders`, all counters non-negative,
  rating in `[0, 500]`, tz-aware `onboarded_at`).
- `Order`, `Return`, `Review` source-record validators.
- `build_fact_seller_day(orders, returns, reviews)` ETL:
  bucket by `(seller_id, day-in-VN_TZ)`, credit returns to the
  originating order's day, bucket reviews on their own day,
  drop empty / orphan-review buckets.
- KPI views: `seller_summary`, `daily_trend`, `top_sellers_by_gmv`,
  `worst_sellers_by_return_rate` — pure functions over fact rows.
- `SellerSummary` properties: `aov_vnd` (integer floor div),
  `return_rate_pct`, `refund_rate_pct`, `avg_rating_x100`,
  `nps_proxy` (linear approximation: avg 5★ → +100, avg 2★ → −100).
- `worst_sellers_by_return_rate(..., min_orders=10)` suppresses the
  "1-order shop with a 100% return rate" noise.
- Seeded synthetic generator producing coherent
  `(orders, returns, reviews)` triples; seller 0 gets a 3× weight
  so leaderboard tests have a stable winner.
- Type-checked JSONL codec for sources + facts with
  `_require_str` / `_require_int` decoders (rejects `bool` for `int`).
- CLI `sellermart info | simulate | build | top | worst | trend | summary`.
- 82 tests including 5 Hypothesis properties (total-orders preserved,
  GMV preserved, `n_unique_buyers ≤ n_orders` per row, output sorted
  by `(seller_id, date_key)`, orphan returns dropped).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `sellermart` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The mart is **sparse**: a seller with no orders on a day produces
  no fact row. Downstream callers do `LEFT JOIN dim_date` if they
  need a dense calendar — this keeps the fact table size proportional
  to actual activity, not to `n_sellers × n_days`.
- A review without a matching order on the same day still produces
  no fact row (the grain demands at least one order). The originating
  order's review counter only catches reviews filed *on* that order's
  day; reviews filed days later show up on the review day's row.
