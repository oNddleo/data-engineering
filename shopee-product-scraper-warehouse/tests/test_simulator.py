"""Simulator + integration tests."""

from __future__ import annotations

from shopeedw.aggregations import summarise, top_sellers_by_gmv
from shopeedw.simulator import generate
from shopeedw.warehouse import Warehouse


def test_generate_reproducible_with_seed():
    s1, p1 = generate(seed=42, n_shops=5, n_products=10)
    s2, p2 = generate(seed=42, n_shops=5, n_products=10)
    assert [s.shop_id for s in s1] == [s.shop_id for s in s2]
    assert [p.item_id for p in p1] == [p.item_id for p in p2]


def test_generate_counts_match_args():
    shops, products = generate(seed=0, n_shops=8, n_products=25)
    assert len(shops) == 8
    assert len(products) == 25


def test_generate_multi_snapshot_per_product():
    shops, products = generate(seed=0, n_shops=2, n_products=3, n_snapshots_per_product=4)
    # 3 products × 4 snapshots = 12 product rows.
    assert len(products) == 12
    # Each (item_id, shop_id) pair should have 4 snapshots.
    counts: dict = {}
    for p in products:
        counts[(p.item_id, p.shop_id)] = counts.get((p.item_id, p.shop_id), 0) + 1
    assert all(c == 4 for c in counts.values())


def test_generate_distinct_item_ids():
    _, products = generate(seed=0, n_shops=3, n_products=20)
    item_ids = {p.item_id for p in products}
    assert len(item_ids) == 20


def test_generate_into_warehouse_passes_aggregations():
    shops, products = generate(seed=0, n_shops=5, n_products=20)
    wh = Warehouse()
    wh.ingest_shops(shops)
    wh.ingest_products(products)
    s = summarise(wh)
    assert s.n_shops == 5
    assert s.n_products == 20


def test_generate_top_sellers_returns_results():
    shops, products = generate(seed=0, n_shops=5, n_products=20)
    wh = Warehouse()
    wh.ingest_shops(shops)
    wh.ingest_products(products)
    rankings = top_sellers_by_gmv(wh, n=3)
    assert len(rankings) >= 1


def test_generate_uses_known_categories():
    from shopeedw.categories import CATEGORIES

    _, products = generate(seed=0, n_products=50)
    for p in products:
        assert p.category_key in CATEGORIES


def test_generate_uses_known_provinces():
    shops, _ = generate(seed=0, n_shops=10)
    expected = {"079", "001", "031", "048", "075", "077", "074", "022", "027", "092"}
    for s in shops:
        assert s.location_province_code in expected
