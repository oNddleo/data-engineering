"""Shopee VN category taxonomy tests."""

from __future__ import annotations

from shopeedw.categories import CATEGORIES, category_id, category_name_vn, is_valid_category


def test_known_categories_resolve():
    assert category_name_vn("fashion_women") == "Thời Trang Nữ"
    assert category_name_vn("food_beverages") == "Thực Phẩm & Đồ Uống"
    assert category_name_vn("electronics") == "Thiết Bị Điện Tử"


def test_unknown_category_returns_none():
    assert category_name_vn("widgets") is None
    assert category_id("widgets") is None


def test_is_valid_category():
    assert is_valid_category("fashion_women")
    assert not is_valid_category("widgets")
    assert not is_valid_category("")


def test_taxonomy_has_22_entries():
    assert len(CATEGORIES) == 22


def test_all_category_ids_unique():
    ids = [v[0] for v in CATEGORIES.values()]
    assert len(set(ids)) == len(ids)


def test_all_display_names_non_empty():
    for _, name in CATEGORIES.values():
        assert name.strip()


def test_taxonomy_covers_key_segments():
    keys = set(CATEGORIES)
    for required in (
        "fashion_women",
        "fashion_men",
        "electronics",
        "beauty_health",
        "mom_baby",
        "food_beverages",
        "appliances",
        "grocery",
    ):
        assert required in keys, required
