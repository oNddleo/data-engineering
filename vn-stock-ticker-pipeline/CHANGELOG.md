# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — `Exchange` (HOSE / HNX / UPCOM), `Ticker`, `OHLCBar`
  (with `daily_change_vnd` + `daily_change_bps`), `Order` with 4
  `OrderKind` values (LO / MP / ATO / ATC) + per-kind invariant
  (LO must have price > 0; MP/ATO/ATC must have price = 0).
* **Exchange directory** — `ExchangeProfile` per board with
  ``price_band_bps`` (700 / 1 000 / 1 500), ``ipo_band_bps``
  (2 000 / 3 000 / 4 000), ``lot_size = 100``, and tick rules.
* **Ticker registry** — VN30 (Q1 2025 composition per Decision
  1/2025/QĐ-SGDCK), 10 HNX leaders, 5 UPCoM leaders. Helpers:
  ``all_tickers``, ``vn30``, ``tickers_on(exchange)``, ``ticker_for``.
* **Pricing rules** — `tick_size` (HOSE tiered 10/50/100, HNX/UPCoM
  flat 100), `round_to_tick` (down/up/nearest), `is_valid_tick`,
  `is_valid_lot`, `ceiling_floor`, `is_within_band`.
* **OHLC bars** — `Trade` + `aggregate_bar` to roll intraday trades
  into a daily bar; sorts by ts_ms internally.
* **Aggregator** — `TickerStats` (high water mark, low water mark,
  total volume, period change), `moving_average_close(bars, n)`,
  `volume_weighted_avg_price`.
* **Anomaly detection** — `find_band_breaches`, `find_volume_spikes`
  (sliding 5-bar window, 5× multiplier), `find_price_gaps`
  (500 bps default threshold).
* **Simulator** — `generate(n_tickers, n_days, seed)` produces a
  realistic OHLC stream that skips weekends and respects exchange
  tick + lot rules; configurable cohorts inject band breaches and
  10× volume spikes.
* **CLI** — `info | exchanges | tickers | band | tick | simulate |
  summary | anomaly`. `anomaly` exits 2 when any finding fires.
* **JSONL codec** — round-trip for `OHLCBar`, `Order`, `TickerStats`,
  `AnomalyFinding`.
* **Quality gate** — 157 tests with Hypothesis property tests
  (tick size positive, round-to-tick monotonicity, IPO band wider
  than normal, OHLC ordering invariants, VWAP bounded by min/max
  close, stats volume conservation). `mypy --strict` clean; ruff
  lint + format clean; zero runtime deps.
