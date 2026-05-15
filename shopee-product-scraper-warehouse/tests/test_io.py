"""JSONL codec tests."""

from __future__ import annotations

from shopeedw.io_jsonl import (
    dump_products,
    dump_shops,
    load_products,
    load_shops,
    product_from_dict,
    product_to_dict,
    shop_from_dict,
    shop_to_dict,
)

from ._fixtures import make_product, make_shop


def test_product_round_trip():
    p = make_product()
    assert product_from_dict(product_to_dict(p)) == p


def test_shop_round_trip():
    s = make_shop()
    assert shop_from_dict(shop_to_dict(s)) == s


def test_dump_load_products():
    ps = [make_product(item_id=500_000_000 + i) for i in range(5)]
    loaded = list(load_products(dump_products(ps)))
    assert loaded == ps


def test_dump_load_shops():
    ss = [make_shop(shop_id=100_000 + i) for i in range(3)]
    loaded = list(load_shops(dump_shops(ss)))
    assert loaded == ss


def test_load_skips_blank_lines():
    text = "\n\n" + dump_products([make_product()])
    assert len(list(load_products(text))) == 1
