"""MockShopeeScraper tests."""

from __future__ import annotations

import pytest

from shopeedw.scraper import MockShopeeScraper

from ._fixtures import make_product, make_shop


def test_mock_lookup_product():
    sc = MockShopeeScraper(products=[make_product()])
    p = sc.fetch_product(500_000_001, 100_000)
    assert p is not None
    assert p.item_id == 500_000_001


def test_mock_returns_none_for_unknown_product():
    sc = MockShopeeScraper()
    assert sc.fetch_product(1, 1) is None


def test_mock_lookup_shop():
    sc = MockShopeeScraper(shops=[make_shop()])
    s = sc.fetch_shop(100_000)
    assert s is not None and s.name == "Test Shop"


def test_mock_register_product():
    sc = MockShopeeScraper()
    sc.register_product(make_product(item_id=999))
    assert sc.fetch_product(999, 100_000) is not None


def test_mock_size_properties():
    sc = MockShopeeScraper(
        products=[make_product(item_id=1), make_product(item_id=2)],
        shops=[make_shop(shop_id=100_000), make_shop(shop_id=100_001)],
    )
    assert sc.n_products == 2
    assert sc.n_shops == 2


def test_list_by_category_filters():
    sc = MockShopeeScraper(
        products=[
            make_product(item_id=1, category_key="fashion_women", sold=100, price=100_000),
            make_product(item_id=2, category_key="fashion_women", sold=50, price=100_000),
            make_product(item_id=3, category_key="electronics", sold=200, price=500_000),
        ]
    )
    out = list(sc.list_products_by_category("fashion_women", limit=10))
    assert {p.item_id for p in out} == {1, 2}


def test_list_by_category_sorted_by_gmv():
    sc = MockShopeeScraper(
        products=[
            make_product(item_id=1, category_key="fashion_women", sold=100, price=100_000),  # 10M
            make_product(item_id=2, category_key="fashion_women", sold=50, price=300_000),  # 15M
        ]
    )
    out = list(sc.list_products_by_category("fashion_women", limit=10))
    assert [p.item_id for p in out] == [2, 1]  # higher GMV first


def test_list_by_category_respects_limit():
    sc = MockShopeeScraper(
        products=[make_product(item_id=i, category_key="electronics") for i in range(1, 6)]
    )
    out = list(sc.list_products_by_category("electronics", limit=3))
    assert len(out) == 3


def test_list_by_category_rejects_zero_limit():
    sc = MockShopeeScraper()
    with pytest.raises(ValueError):
        list(sc.list_products_by_category("fashion_women", limit=0))
