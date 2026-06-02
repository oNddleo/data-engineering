# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Platform` enum (`SHOPEE`, `LAZADA`, `TIKI`) covering the three
  biggest VN e-commerce marketplaces.
- `SkuMapping` + `SkuRegistry` for bidirectional canonical-SKU
  ↔ `(platform, platform_item_id)` lookup. Registry rejects
  re-mapping to a *different* canonical SKU (almost always a bug
  in the upstream product-matching pipeline) but is idempotent on
  exact duplicates.
- `ProductObservation` data type with same invariants as the
  single-platform schema: positive integer VND, `original_price ≥
  price`, non-negative stock, tz-aware datetimes.
- `ObservationStore` — `bisect`-sorted per-`(sku, platform)`
  observation series with `latest`, `all_latest_for_sku`,
  `history(since, until)` queries. O(log n) range queries.
- Four pure detector functions:
  - `detect_price_changes` — UP/DOWN/SAME with `min_pct_change`
    threshold; reports only the most-recent transition per series.
  - `detect_arbitrage` — cross-platform spread above
    `min_spread_pct`. Skips out-of-stock observations (you can't
    arbitrage what you can't buy). Requires ≥ 2 in-stock platforms.
  - `detect_stockouts` — latest observation with `stock == 0`.
  - `detect_below_map` — current price below manufacturer's MAP
    (caller supplies a `{sku: map_vnd}` table).
- Four event types (`PriceChangeEvent`, `ArbitrageEvent`,
  `StockoutEvent`, `BelowMapEvent`) plus `Direction` (UP/DOWN/SAME)
  and `EventKind` enum.
- Seeded synthetic generator with two injection knobs:
  `arbitrage_skus` (adds a 25 % platform-price wedge) and
  `stockout_skus` (sets last-snapshot stock to 0 on one platform).
- JSONL codec for `SkuMapping` and `ProductObservation` with
  type-checked decoders.
- `multiprice` CLI: `info`, `simulate`, `changes`, `arbitrage`,
  `stockouts`, `summary`.
- **75 tests** including 5 Hypothesis properties.
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `mp` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- This project is intentionally complementary to
  `shopee-product-scraper-warehouse`. That one is single-platform
  (top sellers, categories, price drops within Shopee). This one is
  multi-platform (cross-platform arbitrage, stockouts across all
  three). Different question, different data model — keeping them
  separate avoids the temptation to over-generalise.
- `detect_arbitrage` filters out out-of-stock observations
  deliberately. A 30 % "arbitrage" on a product you can't actually
  buy is a data-quality alert, not a business opportunity.
- The hard part of multi-platform tracking is the SKU mapping
  itself (which platform listings = same product?). We treat that
  as an upstream concern — `SkuRegistry` just stores the answers
  the product-matching pipeline produces. The README documents the
  usual approaches: barcode, fuzzy text, image embeddings, human
  curation.
- One event per series for price changes — only the most-recent
  transition. To get full historical changes, iterate per-pair and
  call `detect_price_changes` on successively bounded `since`
  windows.
