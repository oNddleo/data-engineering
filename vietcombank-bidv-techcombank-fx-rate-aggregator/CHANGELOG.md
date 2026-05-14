# Changelog

## [0.1.0] — 2026-05-14

### Added
- `Bank` enum covering the top-10 VN commercial banks (VCB, BIDV,
  TCB, MB, VPB, ACB, VTB, AGB, HDB, TPB).
- `Currency` enum for the 11 currencies VN banks routinely quote
  (USD/EUR/JPY/GBP/AUD/SGD/CNY/KRW/THB/HKD/CAD).
- Frozen `Quote` + `Snapshot` dataclasses with strict invariants
  (positive amounts, tz-aware timestamps, snapshot/quote bank
  consistency) and derived `bid_ask_spread_vnd` /
  `bid_ask_spread_pct` helpers.
- Four bundled vendor parsers:
  - **Vietcombank XML** — `<ExrateList>` feed with naïve local
    `yyyy-MM-dd HH:mm:ss` timestamp tagged UTC+7 at parse time.
  - **BIDV HTML** — stdlib `html.parser` extractor for the rate
    table; explicit `quoted_at` argument since the page has no
    machine-readable timestamp.
  - **Techcombank JSON** — REST-API shape with full ISO-8601
    offset preserved.
  - **Generic CSV** — `currency,buy_cash,buy_transfer,sell` for any
    bank willing to publish CSV directly.
- All parsers raise a single `ParseError(vendor, field, message)` on
  malformed input; unknown currency codes are silently skipped.
- `TimeSeriesStore` — in-memory `bisect`-sorted per-series TSDB
  with `append_quote` / `append_snapshot` (idempotent on exact
  duplicates), `latest`, `history`, `all_latest`, `as_of`.
- JSONL codec (`dump_quotes` / `load_quotes`) + file persistence
  (`save_store` / `load_store`) with type-checked decoders so
  malformed payloads fail loud at the boundary.
- `analyze()` — cross-bank spread analyser with 4 alert kinds:
  `INVERTED_SPREAD` (CRIT, short-circuits outlier checks),
  `BUY_OUTLIER` / `SELL_OUTLIER` (WARN, requires ≥ 3 banks for
  meaningful median), `STALE_QUOTE` (INFO, opt-in via
  `reference_time`).
- Seeded synthetic generator (`simulator.generate`) with 4
  anomaly-injection kinds: `outlier_buy`, `outlier_sell`,
  `inverted`, `stale`.
- `fxagg` CLI: `info`, `parse --format {vcb-xml,bidv-html,tcb-json,generic-csv}`,
  `analyze`, `simulate`. Pipe-friendly.
- **88 tests** including 4 Hypothesis properties.
- mypy `--strict` clean over 7 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `fxagg` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- The `INVERTED_SPREAD` short-circuit means the simulator's
  `outlier_buy` injection bumps both buy *and* sell to keep the row
  non-inverted; otherwise the BUY_OUTLIER alert would never fire on
  the injected row and the corresponding test would be a no-op.
- Outlier detection is skipped when fewer than 3 banks have quotes
  — the median of two values isn't a robust peer baseline.
- JPY mid-price (~170 VND/¥) is small enough that integer
  truncation around the buy/sell endpoints can push the synthetic
  spread up to ~1.8 %; the `test_generate_spread_in_reasonable_range`
  test's upper bound is 2.0 % to accommodate this.
- `TimeSeriesStore.append_quote` keys idempotency on the full Quote
  equality — same bank, currency, timestamp, *and* all amounts. A
  late-arriving correction with different amounts would be treated
  as a new row (a desirable property for FX audit trails).
