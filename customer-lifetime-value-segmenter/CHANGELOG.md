# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Customer`, `Order`, `RFMScore` frozen-slots dataclasses with
  validation at construction (tz-aware datetimes, positive amounts,
  non-empty IDs, R/F/M scores in `[1, 5]`).
- `Segment` enum with the 10 standard CRM segments (CHAMPIONS,
  LOYAL_CUSTOMERS, POTENTIAL_LOYALISTS, NEW_CUSTOMERS,
  NEED_ATTENTION, ABOUT_TO_SLEEP, AT_RISK, CANT_LOSE_THEM,
  HIBERNATING, LOST).
- `rfm.score(customers, orders, as_of) → list[RFMScore]` —
  population-relative quintile scoring with R inverted (recent =
  high). Never-bought customers short-circuited to `F=1, M=1` to
  prevent the degenerate "everyone is a champion in a tiny
  zero-only population" case.
- `_quintile_score` uses strict `>` boundaries so the bottom-quintile
  value lands in score 1, not score 2 (population `[1, 2, 3, 4, 5]`:
  value 1 → score 1; value 5 → score 5).
- `segments.rfm_to_segment(r, f, m) → Segment` — pure mapping
  function. `m` is part of the signature for forward-compatibility
  but the canonical mapping ignores it.
- `segments.classify_all`, `segment_distribution`,
  `top_in_segment`, `transitions` — composable functions for
  cohort dashboards.
- `clv.forecast` — historical-CLV formula
  `AOV × frequency × expected_lifetime / window` with segment-aware
  lifetime lookup (CHAMPIONS = 1095 days, LOST = 0 days).
  Caller-supplied `lifetime_days` map overrides defaults per
  vertical.
- `clv.total_clv_by_segment`, `top_clv` — portfolio rollups.
- Seeded synthetic generator (`simulator.generate`) producing
  customers + orders across 9 behavioural archetypes (champion,
  loyal, potential, new, attention, sleep, atrisk, hibernate,
  lost) with realistic VN-marketplace distributions.
- Type-checked JSONL codec for Customer / Order / RFMScore /
  CLVForecast with `_require_str` / `_require_int` decoders.
- CLI `clvseg info | simulate | score | segment | clv | top | summary`.
- 79 tests + 5 Hypothesis properties (RFM-to-segment mapping is
  total over the 125-cell cube, R=5/F=5 ⇒ CHAMPIONS, R=1/F=1 ⇒
  LOST, CLV ≥ 0 for any input, segment lifetime always matches
  lookup).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `clvseg` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The first cut of `_quintile_score` used `>=` boundaries, which
  put a customer with the lowest frequency into the *second*
  quintile rather than the first. Switched to strict `>` so
  population `[1, 2, 3, 4, 5]` produces scores `[1, 2, 3, 4, 5]`.
  This also fixed the single-customer-no-orders edge case where the
  buyer was being classified as a champion (pct=1.0 against a
  zero-only population).
- The never-bought short-circuit applies *only* to F and M. R is
  still quintile-scored against the population's recency
  distribution — a customer registered yesterday with no orders
  should still get R=5 (they're recently engaged with the platform,
  just not buying yet).
- Segment-transition counting deliberately excludes customers that
  appear in only one snapshot. New acquisitions and churn are
  separate dashboards with different alert thresholds.
