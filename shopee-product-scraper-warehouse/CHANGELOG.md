# Changelog

## [0.1.0] — 2026-05-15

### Added
- 22-entry Shopee VN top-level category registry with canonical
  Vietnamese display names ("Thời Trang Nữ", "Điện Thoại & Phụ
  Kiện", "Bách Hoá Online", …) and Shopee internal IDs.
- `ShopeeProduct` + `ShopeeShop` dataclasses with integer-only VND
  amounts (no floats) and ratings stored as `int × 100` to avoid
  float drift over millions of products. Strict invariants:
  positive IDs / amounts, `original_price >= price`, ratings in
  `[0, 500]`, response-rate in `[0, 100]`, tz-aware datetimes.
- `ShopeeScraper` Protocol with three methods: `fetch_product`,
  `fetch_shop`, `list_products_by_category`. Bundle
  `MockShopeeScraper` for tests; production swaps in an HTTP client
  with the same signature.
- `Warehouse` composite of three tables:
  - `ProductFacts` — replace-on-newer / drop-on-late-arrival
    semantics keyed by `(item_id, shop_id)`.
  - `ShopFacts` — same semantics keyed by `shop_id`.
  - `PriceHistory` — append-only, bisect-sorted by time with
    optional `(since, until)` window queries and `min_max` summary.
- Five aggregation queries (`top_sellers_by_gmv`,
  `top_sellers_by_volume`, `top_categories_by_gmv`,
  `category_breakdown`, `price_drops`) plus `summarise` for a
  top-line dashboard header. All pure functions over a Warehouse.
- `price_drops` requires `min_history_points` snapshots before
  firing, to avoid false alarms on newly-listed items.
- Seeded synthetic generator producing reproducible Shopee-shaped
  datasets across all 22 categories, with configurable
  multi-snapshot price evolution.
- JSONL codec with type-checked decoders. CLI dataset directory
  format: `shops.jsonl` + `products.jsonl`.
- `shopeedw` CLI with subcommands `info`, `simulate`,
  `top-sellers`, `top-categories`, `price-drops`, `summary`.
- **94 tests** including 4 Hypothesis properties (product +
  shop JSONL round-trip, warehouse ingest count, GMV identity for
  any positive price).
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `shopee` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- Test factories default `original_price = price` when the caller
  doesn't pass one. The first iteration of the fixture had a fixed
  `original_price = 299_000` which collided with tests passing
  larger custom prices — 14 tests failed with the invariant
  violation before the fix.
- We deliberately don't ship an HTTP scraper for Shopee. Building
  one responsibly (rate limiting, retries, captcha handling, ToS
  compliance) is a larger undertaking than the data-model work,
  and shipping it half-baked would invite ToS issues. The
  `ShopeeScraper` Protocol is the right place to plug the real
  scraper in.
- Ratings as `int × 100` was tempting to skip — "just use float"
  — but on aggregations across 1M+ products the accumulated float
  drift becomes visible in the third decimal place. Integers stay
  exact.
