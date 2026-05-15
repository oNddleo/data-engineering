# multi-platform-price-tracker

Track giá same-SKU trên **Shopee / Lazada / Tiki** simultaneously,
detect price-change events, cross-platform arbitrage opportunities,
stockouts, và MAP (Minimum Advertised Price) breaches. Complement
to [`shopee-product-scraper-warehouse`](../shopee-product-scraper-warehouse/)
(which is single-platform).

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **SKU mapping registry** — `(Platform, platform_item_id) →
   canonical_sku`. Curated upstream by a product-matching pipeline
   (barcode lookup, ML matcher); we just store + serve the table.
2. **Observation store** — time-sorted per `(sku, platform)` series
   with `bisect`-backed inserts and range queries.
3. **Four detectors**:
   - `detect_price_changes` — UP/DOWN/SAME between consecutive
     observations on the same platform, with `min_pct_change`
     threshold.
   - `detect_arbitrage` — same SKU's spread between cheapest and
     most-expensive in-stock platform exceeds `min_spread_pct`.
   - `detect_stockouts` — latest observation has `stock == 0`.
   - `detect_below_map` — current price below manufacturer's
     minimum advertised price.

## Event types

| Event              | Severity meaning                                  |
| ------------------ | ------------------------------------------------- |
| `PRICE_CHANGE`     | Operator-actionable: monitor competitive moves    |
| `ARBITRAGE`        | Resale opportunity OR data-quality issue          |
| `STOCKOUT`         | Customer-impacting; trigger re-stock workflow     |
| `BELOW_MAP`        | Compliance: manufacturer enforces minimum price   |

## Why it's distinct from shopee-product-scraper-warehouse

`shopee-product-scraper-warehouse` is **single-platform** —
top-seller rankings, category aggregates, price drops within
Shopee. This project is **multi-platform** — it asks "is the same
product priced differently across Shopee, Lazada, and Tiki right
now?". Different question, different data model (SKU mapping
registry is the centrepiece), different output (cross-platform
arbitrage events that don't exist in a single-platform view).

## Components

| Module                | Role                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `multiprice.schema`   | `Platform`, `ProductObservation`, `SkuMapping`, `VN_TZ`             |
| `multiprice.mapping`  | `SkuRegistry` — bidirectional canonical-SKU ↔ platform-item id     |
| `multiprice.store`    | `ObservationStore` — `bisect`-sorted per-`(sku, platform)` series   |
| `multiprice.events`   | `PriceChangeEvent`, `ArbitrageEvent`, `StockoutEvent`, `BelowMapEvent` |
| `multiprice.detectors`| 4 pure detector functions                                            |
| `multiprice.simulator`| Seeded synthetic generator with controllable arbitrage + stockout injection |
| `multiprice.io_jsonl` | JSONL codec                                                          |
| `multiprice.cli`      | `multiprice info | simulate | changes | arbitrage | stockouts | summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
multiprice info

# 1) Synthesise a dataset across 8 SKUs × 3 platforms × 4 snapshots,
#    with arbitrage + stockout patterns injected.
multiprice simulate \
  --skus 8 --snapshots 4 \
  --arbitrage 2 --stockouts 1 \
  --seed 42 --output ./data

# 2) Cross-platform arbitrage opportunities.
multiprice arbitrage --dataset ./data --min-spread 10

# 3) Stockouts.
multiprice stockouts --dataset ./data

# 4) Price changes (between the last two snapshots per series).
multiprice changes --dataset ./data --min-pct 2

# 5) Summary JSON.
multiprice summary --dataset ./data
```

End-to-end output on an 8-SKU × 4-snapshot dataset:

```
$ multiprice arbitrage --dataset ./data --min-spread 10
sku                    cheapest        price expensive          price   spread
SKU-8000000000         TIKI          183,598 LAZADA           209,526  14.12%
SKU-8000000001         SHOPEE         90,573 LAZADA           106,202  17.26%
SKU-8000000005         SHOPEE        173,976 LAZADA           192,543  10.67%

total: 3 arbitrage opportunities (≥ 10.0%)

$ multiprice summary --dataset ./data
{
  "n_observations": 96,
  "n_skus": 8,
  "n_series": 24,
  "n_price_changes": 24,
  "n_arbitrage_opportunities": 3,
  "n_stockouts": 1
}
```

## Library

```python
from multiprice import (
    ObservationStore, SkuRegistry, generate,
    detect_arbitrage, detect_price_changes, detect_stockouts, detect_below_map,
)

mappings, observations = generate(seed=42, n_skus=20, n_snapshots=4, arbitrage_skus=5)
store = ObservationStore()
store.append_many(observations)
registry = SkuRegistry()
registry.register_many(mappings)

for event in detect_arbitrage(store, min_spread_pct=10):
    print(f"{event.canonical_sku}: cheapest on {event.cheapest_platform.value} "
          f"at {event.cheapest_price_vnd:,} VND, "
          f"spread {event.spread_pct:.1f}%")

# MAP breach detection — supply the manufacturer's enforced minimums:
map_table = {"SKU-8000000000": 200_000, "SKU-8000000005": 180_000}
for event in detect_below_map(store, map_table):
    print(f"{event.canonical_sku} on {event.platform.value} priced "
          f"{event.current_price_vnd:,} (MAP {event.map_vnd:,}, breach {event.breach_vnd:,})")
```

## SKU mapping note

The hard part of multi-platform tracking is figuring out **which
listings on Shopee, Lazada, Tiki correspond to the same physical
product**. We treat that as an upstream concern — `SkuRegistry`
just stores the table the product-matching pipeline produces.

Real production matching uses some combination of:

* **Barcodes** (GTIN/EAN/UPC) — when sellers fill them in honestly.
* **Brand + model + variant text matching** — fuzzy match across
  product titles.
* **Image embeddings** — `CLIP`/`DINOv2` similarity above a threshold.
* **Human curation** — for high-volume SKUs, an analyst confirms.

A correctly-populated `SkuRegistry` is the prerequisite for every
detector in this project. Garbage in → garbage out.

## Quality

```bash
make test       # 75 tests, 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **75 tests** covering schema invariants, registry semantics
  (bidirectional lookup, duplicate-different-SKU rejection),
  observation store (sort order, time-window queries), all 4
  detectors with explicit edge cases (no history, equal prices,
  one-platform arbitrage, in-stock filtering), and 5 Hypothesis
  properties.
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `mp` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
