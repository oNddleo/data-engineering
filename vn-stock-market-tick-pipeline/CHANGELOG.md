# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Exchange` enum for VN trading venues (HOSE, HNX, UPCOM) with
  daily price-band (±7% / ±10% / ±15%) and lot-size (100) rules
  baked in as lookup tables.
- `Symbol`, `Tick`, `OHLCVBar` frozen-slots dataclasses with
  validation at construction (tz-aware datetimes, ASCII uppercase
  codes, positive money, OHLC consistency `low ≤ open/close ≤ high`).
- `ceiling_price` + `floor_price` — daily price band per exchange.
- `is_in_session(ts)` — tz-aware check covering morning (09:00 —
  11:30) and afternoon (13:00 — 14:45) sessions in `VN_TZ`.
- `resample(ticks, interval) → list[OHLCVBar]` — left-closed bars
  at 1m / 5m / 15m / 1h / 1d intervals, aligned to `VN_TZ` epoch
  boundaries. Sparse output: zero-tick buckets dropped. Single-tick
  buckets produce degenerate doji bars (OHLC all equal).
- Indicators: `sma`, `ema` (SMA-seeded), `rsi` (Wilder's smoothed
  averaging), `macd` (12/26/9 EMA-of-EMA + histogram), `bollinger`
  (population σ, `n_std=2.0` default).
- `find_circuit_breaker_hits` — flags bars whose `high_vnd ≥ ceiling`
  or `low_vnd ≤ floor` based on per-symbol previous close.
- `find_unusual_volume` — z-score detection over a trailing history
  window; skips symbols with fewer than 5 history points (cold-start
  tolerance) and σ=0 series (no division blowup).
- `compute_index`, `vn_index`, `vn30_index`, `hnx_index` —
  market-cap-weighted index calculation with halted-symbol
  tolerance (missing price → contributes 0, matching the official
  methodology of substituting the last known print).
- Seeded synthetic tick generator (`simulator.generate`) for 11 real
  VN blue-chips (VIC, VHM, HPG, VCB, VNM, FPT, MSN, MWG, ACB, SHB,
  BCG). Geometric random walk inside the daily band; ticks only
  emitted during in-session minutes. `ceiling_hit_codes` parameter
  forces selected symbols' first ticks to print at the ceiling for
  anomaly-path testing.
- Type-checked JSONL codec with `_require_str` / `_require_int`
  decoders (rejects `bool` for `int`, unknown exchange / state
  values rejected at parse time).
- CLI `vntick info | simulate | resample | indicators | anomalies | index | summary`.
- 93 tests including 5 Hypothesis properties (OHLC invariants always
  hold, total volume / trade count preserved across resampling, SMA
  bounded by window min/max, Bollinger upper ≥ middle ≥ lower).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vntick` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The resampler **sorts ticks internally** rather than relying on
  callers to pre-sort. Live tick feeds often arrive slightly
  out-of-order due to multi-server fanout — assuming pre-sorted
  input was the recurring bug in the v0 reference implementation
  this replaces.
- RSI uses **Wilder's smoothed averaging**, not the naïve
  ``avg_gain / avg_loss`` over a rolling window. The smoothed
  variant is what TradingView, MetaTrader, and Vietnamese broker
  UIs (VPS, SSI iBoard) display — using anything else creates
  off-by-N-bars discrepancies operators don't tolerate.
- The 1-day bar floors to `00:00 VN_TZ`, not UTC midnight. A trade
  at 13:00 VN on Mon should produce a Monday daily bar, not a
  Sunday one — and that requires the tz conversion before
  flooring (the recurring bug in non-VN-aware market-data libs).
- `unusual_volume` is *not* meant to fire during the first hour
  of the session — daily volumes haven't completed yet. Callers
  typically run it post-close against same-time-of-day history,
  but the function itself is agnostic; it just computes z-scores.
