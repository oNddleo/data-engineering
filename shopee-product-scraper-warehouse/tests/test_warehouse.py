"""Warehouse table tests."""

from __future__ import annotations

from shopeedw.warehouse import PriceHistory, ProductFacts, ShopFacts, Warehouse

from ._fixtures import make_product, make_shop, t_at


def test_product_facts_upsert_returns_true_for_new():
    pf = ProductFacts()
    assert pf.upsert(make_product()) is True
    assert len(pf) == 1


def test_product_facts_upsert_returns_true_when_newer_replaces_older():
    pf = ProductFacts()
    pf.upsert(make_product(price=200_000, fetched_at=t_at(0)))
    assert pf.upsert(make_product(price=180_000, fetched_at=t_at(60))) is True
    assert pf.get(500_000_001, 100_000).price_vnd == 180_000  # type: ignore[union-attr]


def test_product_facts_upsert_drops_late_arriving():
    pf = ProductFacts()
    pf.upsert(make_product(price=180_000, fetched_at=t_at(60)))
    assert pf.upsert(make_product(price=200_000, fetched_at=t_at(0))) is False
    assert pf.get(500_000_001, 100_000).price_vnd == 180_000  # type: ignore[union-attr]


def test_product_facts_get_missing():
    assert ProductFacts().get(1, 1) is None


def test_product_facts_by_category():
    pf = ProductFacts()
    pf.upsert(make_product(item_id=1, category_key="fashion_women"))
    pf.upsert(make_product(item_id=2, category_key="electronics"))
    assert len(pf.by_category("fashion_women")) == 1
    assert len(pf.by_category("electronics")) == 1


def test_product_facts_by_shop():
    pf = ProductFacts()
    pf.upsert(make_product(item_id=1, shop_id=1))
    pf.upsert(make_product(item_id=2, shop_id=1))
    pf.upsert(make_product(item_id=3, shop_id=2))
    assert len(pf.by_shop(1)) == 2
    assert len(pf.by_shop(2)) == 1


def test_shop_facts_upsert():
    sf = ShopFacts()
    sf.upsert(make_shop())
    assert sf.get(100_000) is not None


def test_shop_facts_late_arriving_dropped():
    sf = ShopFacts()
    sf.upsert(make_shop(name="New", fetched_at=t_at(60)))
    sf.upsert(make_shop(name="Old", fetched_at=t_at(0)))
    assert sf.get(100_000).name == "New"  # type: ignore[union-attr]


def test_price_history_append_and_retrieve():
    ph = PriceHistory()
    for i in range(5):
        ph.append(make_product(price=100_000 + i * 10, fetched_at=t_at(i * 10)))
    hist = ph.history(500_000_001, 100_000)
    assert len(hist) == 5
    assert [h[1] for h in hist] == [100_000, 100_010, 100_020, 100_030, 100_040]


def test_price_history_sorted_by_time():
    ph = PriceHistory()
    ph.append(make_product(price=100, fetched_at=t_at(30)))
    ph.append(make_product(price=200, fetched_at=t_at(0)))
    ph.append(make_product(price=150, fetched_at=t_at(15)))
    hist = ph.history(500_000_001, 100_000)
    times = [t for t, _ in hist]
    assert times == sorted(times)


def test_price_history_window():
    ph = PriceHistory()
    for i in range(5):
        ph.append(make_product(price=100_000 + i, fetched_at=t_at(i * 10)))
    out = ph.history(500_000_001, 100_000, since=t_at(15), until=t_at(35))
    # Should include t_at(20), t_at(30).
    assert len(out) == 2


def test_price_history_min_max():
    ph = PriceHistory()
    for price in (100_000, 200_000, 50_000, 150_000):
        ph.append(make_product(price=price, fetched_at=t_at(price)))
    assert ph.min_max(500_000_001, 100_000) == (50_000, 200_000)


def test_price_history_min_max_missing():
    assert PriceHistory().min_max(1, 1) is None


def test_warehouse_ingest_product():
    wh = Warehouse()
    p = make_product()
    wh.ingest_product(p)
    assert len(wh.products) == 1
    assert len(wh.price_history) == 1


def test_warehouse_ingest_products_bulk():
    wh = Warehouse()
    wh.ingest_products([make_product(item_id=i) for i in range(1, 4)])
    assert len(wh.products) == 3


def test_warehouse_ingest_shop():
    wh = Warehouse()
    wh.ingest_shop(make_shop())
    assert len(wh.shops) == 1


def test_warehouse_ingest_shops_bulk():
    wh = Warehouse()
    wh.ingest_shops([make_shop(shop_id=i) for i in range(100, 105)])
    assert len(wh.shops) == 5
