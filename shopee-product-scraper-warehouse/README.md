# shopee-product-scraper-warehouse

Pluggable scraper Protocol + in-memory warehouse + e-commerce
aggregations cho Shopee VN. **Không bundle HTTP scraper** (tránh ToS
+ brittle test) — production cắm scraper riêng (httpx / aiohttp /
Scrapy) vào cùng Protocol, phần còn lại của codebase (warehouse,
aggregations) chạy được ngay.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Scraper Protocol** — `ShopeeScraper` với 3 methods
   (`fetch_product`, `fetch_shop`, `list_products_by_category`).
   Bundle `MockShopeeScraper` cho tests; production swap với client
   thực qua interface y hệt.
2. **Warehouse** — `Warehouse` chứa 3 bảng:
   - `ProductFacts` — latest snapshot per `(item_id, shop_id)`.
     Replace-on-newer, drop-on-late-arrival.
   - `ShopFacts` — latest snapshot per `shop_id`.
   - `PriceHistory` — append-only time-sorted price series.
3. **Aggregations** — 5 dashboard queries:
   - `top_sellers_by_gmv` — top-N shops by ∑(price × sold)
   - `top_sellers_by_volume` — top-N shops by ∑ sold_count
   - `top_categories_by_gmv` — category GMV ranking
   - `category_breakdown` — full per-category stats
   - `price_drops` — products with current price ≥ N% below historical max
4. **Simulator** — seeded synthetic shops + products covering all
   22 Shopee VN top-level categories, with multi-snapshot price
   evolution for testing price-drop detection.

## The 22 Shopee VN top-level categories

| Key                    | Display name (VN)              |
| ---------------------- | ------------------------------ |
| `fashion_women`        | Thời Trang Nữ                  |
| `fashion_men`          | Thời Trang Nam                 |
| `fashion_kids`         | Thời Trang Trẻ Em              |
| `shoes_women`          | Giày Dép Nữ                    |
| `shoes_men`            | Giày Dép Nam                   |
| `bags_women`           | Túi Ví Nữ                      |
| `bags_men`             | Balo & Túi Ví Nam              |
| `beauty_health`        | Sắc Đẹp                        |
| `mom_baby`             | Mẹ & Bé                        |
| `home_living`          | Nhà Cửa & Đời Sống             |
| `electronics`          | Thiết Bị Điện Tử               |
| `computer_laptop`      | Máy Tính & Laptop              |
| `phones_accessories`   | Điện Thoại & Phụ Kiện          |
| `watches`              | Đồng Hồ                        |
| `sports_outdoor`       | Thể Thao & Du Lịch             |
| `automotive`           | Ô Tô & Xe Máy & Xe Đạp         |
| `appliances`           | Thiết Bị Điện Gia Dụng         |
| `food_beverages`       | Thực Phẩm & Đồ Uống            |
| `books_stationery`     | Sách & Văn Phòng Phẩm          |
| `toys_games`           | Đồ Chơi                        |
| `pet_supplies`         | Vật Phẩm Cho Thú Cưng          |
| `grocery`              | Bách Hoá Online                |

## Components

| Module                  | Role                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `shopeedw.schema`       | `ShopeeProduct`, `ShopeeShop` with strict invariants                |
| `shopeedw.categories`   | 22-entry Shopee VN category registry                                |
| `shopeedw.scraper`      | `ShopeeScraper` Protocol + `MockShopeeScraper`                      |
| `shopeedw.warehouse`    | `ProductFacts`, `ShopFacts`, `PriceHistory`, `Warehouse`            |
| `shopeedw.aggregations` | top-seller / top-category / price-drop / summary queries            |
| `shopeedw.io_jsonl`     | JSONL codec                                                          |
| `shopeedw.simulator`    | Seeded synthetic dataset generator                                   |
| `shopeedw.cli`          | `shopeedw info | simulate | top-sellers | top-categories | price-drops | summary` |

## Money + rating encoding

* All VND amounts are `int`. No floats — VND has no fractional unit.
* Ratings are stored as `int` ×100: 4.85 stars → `485`. Keeps
  aggregations integer-typed and avoids float drift over millions
  of products.

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
shopeedw info

# 1) Synthesise a dataset with multi-snapshot price history.
shopeedw simulate \
  --shops 20 --products 200 --snapshots 4 --interval 60 \
  --seed 42 \
  --output ./data

# 2) Rank top sellers by GMV.
shopeedw top-sellers --dataset ./data --by gmv --n 10

# 3) Rank top categories.
shopeedw top-categories --dataset ./data --n 5

# 4) List products with significant price drops (≥ 15% from max).
shopeedw price-drops --dataset ./data --threshold 15 --min-history 3

# 5) Dump warehouse summary.
shopeedw summary --dataset ./data
```

End-to-end output on a 5-shop / 30-product / 4-snapshot synthetic dataset:

```
$ shopeedw top-sellers --dataset ./data --by gmv --n 5
shop_id            gmv_vnd    units  name
100002      19,189,231,330   17,047  RPBQ Store
100000      18,335,830,839   17,101  Shop HDRB
100003      12,558,555,826   17,700  DCHV Official
100001       6,188,894,279   21,133  Shop FCLF

$ shopeedw top-categories --dataset ./data --n 3
category_key                   gmv_vnd    units name_vn
mom_baby                12,800,460,342   12,112 Mẹ & Bé
phones_accessories      11,720,634,171   10,837 Điện Thoại & Phụ Kiện
food_beverages           5,875,880,758    3,971 Thực Phẩm & Đồ Uống

$ shopeedw price-drops --dataset ./data --threshold 15
found 26 drops over 15.0% (min 3 history points)
  item=500000003 shop=100003 drop=32.0%  84,698 → 57,595  Cáp sạc CMZ type-C
  item=500000009 shop=100002 drop=30.3%  731,441 → 509,570  Nồi cơm điện SFS 1.8L
```

## Library

```python
from shopeedw import (
    Warehouse, generate,
    top_sellers_by_gmv, top_categories_by_gmv, price_drops, summarise,
)

shops, products = generate(n_shops=20, n_products=200, n_snapshots_per_product=4, seed=42)
wh = Warehouse()
wh.ingest_shops(shops)
wh.ingest_products(products)

print(f"warehouse: {summarise(wh).n_products} products, total GMV {summarise(wh).total_gmv_vnd:,}")
for r in top_sellers_by_gmv(wh, n=10):
    print(r.shop_id, r.shop_name, f"{r.total_gmv_vnd:,} VND", r.total_units_sold)
```

## Production scraper note

Don't ship a half-baked HTTP scraper for Shopee. Their `robots.txt`
forbids bulk crawling; their JS-rendered product pages need a real
browser or an undocumented private API; and rate limits are
aggressive. A correct production scraper needs:

* Proper auth + session handling (cookies, captcha)
* Rate limiting with backoff
* Retry on 429 / 5xx
* Distributed scheduler (Celery / Airflow / Temporal)
* Respect for `robots.txt` and Shopee's ToS

The `ShopeeScraper` Protocol in this codebase is the right
interface to put behind that stack. Everything downstream
(warehouse + aggregations) works against any conforming
implementation.

## Quality

```bash
make test       # 94 tests, 4 Hypothesis properties
make type       # mypy --strict
make lint
```

- **94 tests** covering schema invariants, the 22-category
  taxonomy, scraper Protocol behaviours, warehouse table semantics
  (late-arrival drop, time-window queries, min/max history), all 5
  aggregations, and 4 Hypothesis properties.
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `shopee` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
