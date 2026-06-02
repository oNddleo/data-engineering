"""Aggregations tests."""

from __future__ import annotations

import pytest

from shopeedw.aggregations import (
    category_breakdown,
    price_drops,
    summarise,
    top_categories_by_gmv,
    top_sellers_by_gmv,
    top_sellers_by_volume,
)
from shopeedw.warehouse import Warehouse

from ._fixtures import make_product, make_shop, t_at


def _warehouse_with_data():
    wh = Warehouse()
    # 3 shops, 3 products each, different GMV profiles.
    wh.ingest_shop(make_shop(shop_id=1, name="Shop A"))
    wh.ingest_shop(make_shop(shop_id=2, name="Shop B"))
    wh.ingest_shop(make_shop(shop_id=3, name="Shop C"))
    # Shop 1: 3 products, total GMV ~30M
    for i in range(3):
        wh.ingest_product(
            make_product(
                item_id=100 + i, shop_id=1, price=100_000, sold=100, category_key="fashion_women"
            )
        )
    # Shop 2: 2 products, total GMV ~50M
    for i in range(2):
        wh.ingest_product(
            make_product(
                item_id=200 + i, shop_id=2, price=500_000, sold=50, category_key="electronics"
            )
        )
    # Shop 3: 1 high-volume product, GMV ~100M
    wh.ingest_product(
        make_product(item_id=300, shop_id=3, price=1_000_000, sold=100, category_key="appliances")
    )
    return wh


def test_top_sellers_by_gmv():
    wh = _warehouse_with_data()
    rankings = top_sellers_by_gmv(wh, n=3)
    assert [r.shop_id for r in rankings] == [3, 2, 1]
    assert rankings[0].total_gmv_vnd == 100_000_000


def test_top_sellers_by_volume():
    wh = _warehouse_with_data()
    rankings = top_sellers_by_volume(wh, n=3)
    # Shop 1: 300 units, Shop 2: 100, Shop 3: 100. Ties broken by shop_id.
    assert rankings[0].shop_id == 1
    assert rankings[0].total_units_sold == 300


def test_top_sellers_respects_n():
    wh = _warehouse_with_data()
    assert len(top_sellers_by_gmv(wh, n=2)) == 2


def test_top_sellers_rejects_zero_n():
    with pytest.raises(ValueError):
        top_sellers_by_gmv(_warehouse_with_data(), n=0)


def test_top_sellers_uses_shop_name_when_known():
    wh = _warehouse_with_data()
    rankings = top_sellers_by_gmv(wh, n=3)
    names = {r.shop_id: r.shop_name for r in rankings}
    assert names[1] == "Shop A"


def test_top_sellers_falls_back_when_shop_unknown():
    wh = Warehouse()
    wh.ingest_product(make_product(shop_id=999))
    rankings = top_sellers_by_gmv(wh, n=10)
    assert rankings[0].shop_name == "shop#999"


def test_category_breakdown():
    wh = _warehouse_with_data()
    bd = category_breakdown(wh)
    assert "fashion_women" in bd
    assert "electronics" in bd
    assert "appliances" in bd
    assert bd["fashion_women"].n_products == 3


def test_category_breakdown_carries_vn_display_name():
    wh = _warehouse_with_data()
    bd = category_breakdown(wh)
    assert bd["fashion_women"].category_name_vn == "Thời Trang Nữ"


def test_top_categories_sorts_by_gmv_descending():
    wh = _warehouse_with_data()
    cats = top_categories_by_gmv(wh, n=5)
    gmvs = [c.total_gmv_vnd for c in cats]
    assert gmvs == sorted(gmvs, reverse=True)


def test_price_drops_fires_on_significant_drop():
    wh = Warehouse()
    # 4 snapshots: price drops from 500k to 350k (-30%).
    for i, price in enumerate([500_000, 450_000, 400_000, 350_000]):
        wh.ingest_product(make_product(price=price, fetched_at=t_at(i * 60)))
    drops = price_drops(wh, threshold_pct=20.0, min_history_points=3)
    assert len(drops) == 1
    assert drops[0].drop_pct >= 20.0


def test_price_drops_skips_insufficient_history():
    wh = Warehouse()
    for i, price in enumerate([500_000, 250_000]):  # only 2 history points
        wh.ingest_product(make_product(price=price, fetched_at=t_at(i * 60)))
    assert price_drops(wh, min_history_points=3) == []


def test_price_drops_skips_when_below_threshold():
    wh = Warehouse()
    for i, price in enumerate([500_000, 490_000, 480_000, 475_000]):
        wh.ingest_product(make_product(price=price, fetched_at=t_at(i * 60)))
    assert price_drops(wh, threshold_pct=20.0) == []


def test_price_drops_sorted_by_drop_pct():
    wh = Warehouse()
    # Product A: drops 40%
    for i, price in enumerate([1_000_000, 800_000, 600_000]):
        wh.ingest_product(make_product(item_id=1, price=price, fetched_at=t_at(i * 60)))
    # Product B: drops 30%
    for i, price in enumerate([1_000_000, 800_000, 700_000]):
        wh.ingest_product(make_product(item_id=2, price=price, fetched_at=t_at(i * 60)))
    drops = price_drops(wh, threshold_pct=20.0)
    assert drops[0].drop_pct > drops[1].drop_pct


def test_price_drops_rejects_bad_threshold():
    wh = Warehouse()
    with pytest.raises(ValueError):
        price_drops(wh, threshold_pct=0)
    with pytest.raises(ValueError):
        price_drops(wh, threshold_pct=101)


def test_price_drops_rejects_low_min_history():
    wh = Warehouse()
    with pytest.raises(ValueError):
        price_drops(wh, min_history_points=1)


def test_summarise_overview():
    wh = _warehouse_with_data()
    s = summarise(wh)
    assert s.n_products == 6
    assert s.n_shops == 3
    assert s.total_gmv_vnd > 0
    assert s.by_category["fashion_women"].n_products == 3


def test_top_categories_rejects_zero_n():
    with pytest.raises(ValueError):
        top_categories_by_gmv(Warehouse(), n=0)
