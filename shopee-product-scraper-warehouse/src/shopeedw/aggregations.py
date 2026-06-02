"""Aggregations over the Shopee warehouse.

Five core queries that drive a typical e-commerce dashboard:

* :func:`top_sellers_by_gmv` — top-N shops ranked by sum of
  (price × sold_count) across their products.
* :func:`top_sellers_by_volume` — top-N shops ranked by sum of
  ``sold_count``.
* :func:`top_categories_by_gmv` — category aggregate.
* :func:`price_drops` — products whose current price is below
  ``threshold_pct`` of their observed max.
* :func:`category_breakdown` — counts per category.

Every aggregation is pure: it takes a Warehouse and returns a
dataclass — no mutation, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from shopeedw.categories import category_name_vn

if TYPE_CHECKING:
    from shopeedw.warehouse import Warehouse


@dataclass(frozen=True, slots=True)
class SellerRanking:
    shop_id: int
    shop_name: str
    total_gmv_vnd: int
    total_units_sold: int


@dataclass(frozen=True, slots=True)
class CategoryStats:
    category_key: str
    category_name_vn: str
    n_products: int
    total_gmv_vnd: int
    total_units_sold: int


@dataclass(frozen=True, slots=True)
class PriceDrop:
    item_id: int
    shop_id: int
    name: str
    current_price_vnd: int
    historical_max_vnd: int
    drop_pct: float


# ---------------------------------------------------------------------------
# Seller rankings.


def _seller_aggregates(wh: Warehouse) -> dict[int, tuple[int, int]]:
    """Return ``shop_id → (total_gmv_vnd, total_units)``."""
    out: dict[int, tuple[int, int]] = {}
    for p in wh.products.all():
        gmv, units = out.get(p.shop_id, (0, 0))
        out[p.shop_id] = (gmv + p.gmv_vnd, units + p.sold_count)
    return out


def _shop_name(wh: Warehouse, shop_id: int) -> str:
    s = wh.shops.get(shop_id)
    return s.name if s is not None else f"shop#{shop_id}"


def top_sellers_by_gmv(wh: Warehouse, *, n: int = 10) -> list[SellerRanking]:
    if n <= 0:
        raise ValueError("n must be > 0")
    aggs = _seller_aggregates(wh)
    ranked = sorted(aggs.items(), key=lambda kv: (-kv[1][0], kv[0]))
    return [
        SellerRanking(
            shop_id=shop_id,
            shop_name=_shop_name(wh, shop_id),
            total_gmv_vnd=gmv,
            total_units_sold=units,
        )
        for shop_id, (gmv, units) in ranked[:n]
    ]


def top_sellers_by_volume(wh: Warehouse, *, n: int = 10) -> list[SellerRanking]:
    if n <= 0:
        raise ValueError("n must be > 0")
    aggs = _seller_aggregates(wh)
    ranked = sorted(aggs.items(), key=lambda kv: (-kv[1][1], kv[0]))
    return [
        SellerRanking(
            shop_id=shop_id,
            shop_name=_shop_name(wh, shop_id),
            total_gmv_vnd=gmv,
            total_units_sold=units,
        )
        for shop_id, (gmv, units) in ranked[:n]
    ]


# ---------------------------------------------------------------------------
# Category stats.


def category_breakdown(wh: Warehouse) -> dict[str, CategoryStats]:
    """Per-category aggregate stats. Returns a mapping keyed by category_key."""
    out: dict[str, CategoryStats] = {}
    counts: dict[str, list[int]] = {}
    for p in wh.products.all():
        bucket = counts.setdefault(p.category_key, [0, 0, 0])
        bucket[0] += 1
        bucket[1] += p.gmv_vnd
        bucket[2] += p.sold_count
    for cat, (n, gmv, units) in counts.items():
        out[cat] = CategoryStats(
            category_key=cat,
            category_name_vn=category_name_vn(cat) or cat,
            n_products=n,
            total_gmv_vnd=gmv,
            total_units_sold=units,
        )
    return out


def top_categories_by_gmv(wh: Warehouse, *, n: int = 5) -> list[CategoryStats]:
    if n <= 0:
        raise ValueError("n must be > 0")
    cats = list(category_breakdown(wh).values())
    cats.sort(key=lambda c: (-c.total_gmv_vnd, c.category_key))
    return cats[:n]


# ---------------------------------------------------------------------------
# Price drops.


def price_drops(
    wh: Warehouse,
    *,
    threshold_pct: float = 20.0,
    min_history_points: int = 3,
) -> list[PriceDrop]:
    """Find products whose current price is at least ``threshold_pct`` below
    their observed historical max. Requires at least
    ``min_history_points`` snapshots to avoid false alarms on
    newly-listed items.
    """
    if not 0 < threshold_pct <= 100:
        raise ValueError("threshold_pct must be in (0, 100]")
    if min_history_points < 2:
        raise ValueError("min_history_points must be >= 2")
    out: list[PriceDrop] = []
    for p in wh.products.all():
        history = wh.price_history.history(p.item_id, p.shop_id)
        if len(history) < min_history_points:
            continue
        max_seen = max(price for _, price in history)
        if max_seen == 0:
            continue
        drop = (max_seen - p.price_vnd) / max_seen * 100
        if drop >= threshold_pct:
            out.append(
                PriceDrop(
                    item_id=p.item_id,
                    shop_id=p.shop_id,
                    name=p.name,
                    current_price_vnd=p.price_vnd,
                    historical_max_vnd=max_seen,
                    drop_pct=drop,
                )
            )
    out.sort(key=lambda d: (-d.drop_pct, d.item_id))
    return out


@dataclass(frozen=True, slots=True)
class WarehouseSummary:
    """Top-line counts the dashboard renders in its header."""

    n_products: int
    n_shops: int
    n_price_history_points: int
    total_gmv_vnd: int
    by_category: dict[str, CategoryStats] = field(default_factory=dict)


def summarise(wh: Warehouse) -> WarehouseSummary:
    breakdown = category_breakdown(wh)
    total_gmv = sum(c.total_gmv_vnd for c in breakdown.values())
    return WarehouseSummary(
        n_products=len(wh.products),
        n_shops=len(wh.shops),
        n_price_history_points=len(wh.price_history),
        total_gmv_vnd=total_gmv,
        by_category=breakdown,
    )


__all__ = [
    "CategoryStats",
    "PriceDrop",
    "SellerRanking",
    "WarehouseSummary",
    "category_breakdown",
    "price_drops",
    "summarise",
    "top_categories_by_gmv",
    "top_sellers_by_gmv",
    "top_sellers_by_volume",
]
