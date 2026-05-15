"""SKU registry tests."""

from __future__ import annotations

import pytest

from multiprice.mapping import SkuRegistry
from multiprice.schema import Platform

from ._fixtures import make_mapping


def test_empty_registry():
    r = SkuRegistry()
    assert len(r) == 0
    assert r.n_skus == 0


def test_register_one_mapping():
    r = SkuRegistry()
    r.register(make_mapping())
    assert r.canonical_sku(Platform.SHOPEE, "sp-001") == "SKU-1"


def test_register_bidirectional_lookup():
    r = SkuRegistry()
    r.register(make_mapping(platform=Platform.SHOPEE, platform_item_id="sp-001"))
    r.register(make_mapping(platform=Platform.LAZADA, platform_item_id="lz-001"))
    r.register(make_mapping(platform=Platform.TIKI, platform_item_id="tk-001"))
    platforms = r.platforms_for("SKU-1")
    assert set(platforms.keys()) == {Platform.SHOPEE, Platform.LAZADA, Platform.TIKI}
    assert platforms[Platform.LAZADA] == "lz-001"


def test_register_unknown_platform_returns_none():
    r = SkuRegistry()
    assert r.canonical_sku(Platform.SHOPEE, "missing") is None


def test_register_duplicate_same_sku_idempotent():
    r = SkuRegistry()
    r.register(make_mapping())
    r.register(make_mapping())  # same mapping again — no error
    assert len(r) == 1


def test_register_duplicate_different_sku_raises():
    r = SkuRegistry()
    r.register(make_mapping(canonical_sku="SKU-1"))
    with pytest.raises(ValueError):
        r.register(make_mapping(canonical_sku="SKU-2"))


def test_register_many():
    r = SkuRegistry()
    r.register_many(
        [
            make_mapping(canonical_sku="SKU-1", platform=Platform.SHOPEE, platform_item_id="sp-1"),
            make_mapping(canonical_sku="SKU-1", platform=Platform.LAZADA, platform_item_id="lz-1"),
            make_mapping(canonical_sku="SKU-2", platform=Platform.SHOPEE, platform_item_id="sp-2"),
        ]
    )
    assert r.n_skus == 2
    assert len(r) == 3


def test_all_skus():
    r = SkuRegistry()
    r.register(make_mapping(canonical_sku="A"))
    r.register(make_mapping(canonical_sku="B", platform_item_id="sp-002"))
    assert r.all_skus() == {"A", "B"}


def test_platforms_for_unknown_sku_returns_empty():
    assert SkuRegistry().platforms_for("MISSING") == {}
