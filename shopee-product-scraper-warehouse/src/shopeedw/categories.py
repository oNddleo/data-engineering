"""Shopee VN top-level category taxonomy.

Curated from Shopee.vn's category sidebar. Keys are stable ASCII
identifiers; values are the canonical Vietnamese display names a
shopper sees in the app. The integer numeric column is what
Shopee's internal API uses for filtering (the values match Shopee's
public category endpoints as of 2025).

Keep this list small and high-level — sub-categories explode the
table and don't add information for top-seller analysis.
"""

from __future__ import annotations

CATEGORIES: dict[str, tuple[int, str]] = {
    "fashion_women": (11035567, "Thời Trang Nữ"),
    "fashion_men": (11035831, "Thời Trang Nam"),
    "fashion_kids": (11035922, "Thời Trang Trẻ Em"),
    "shoes_women": (11036132, "Giày Dép Nữ"),
    "shoes_men": (11036025, "Giày Dép Nam"),
    "bags_women": (11036279, "Túi Ví Nữ"),
    "bags_men": (11036452, "Balo & Túi Ví Nam"),
    "beauty_health": (11036558, "Sắc Đẹp"),
    "mom_baby": (11036670, "Mẹ & Bé"),
    "home_living": (11036798, "Nhà Cửa & Đời Sống"),
    "electronics": (11036953, "Thiết Bị Điện Tử"),
    "computer_laptop": (11037179, "Máy Tính & Laptop"),
    "phones_accessories": (11037251, "Điện Thoại & Phụ Kiện"),
    "watches": (11037364, "Đồng Hồ"),
    "sports_outdoor": (11037407, "Thể Thao & Du Lịch"),
    "automotive": (11037485, "Ô Tô & Xe Máy & Xe Đạp"),
    "appliances": (11037529, "Thiết Bị Điện Gia Dụng"),
    "food_beverages": (11037627, "Thực Phẩm & Đồ Uống"),
    "books_stationery": (11037726, "Sách & Văn Phòng Phẩm"),
    "toys_games": (11037830, "Đồ Chơi"),
    "pet_supplies": (11037933, "Vật Phẩm Cho Thú Cưng"),
    "grocery": (11038020, "Bách Hoá Online"),
}
"""Map ``key → (shopee_internal_id, display_name)``. 22 top-level slugs."""


def category_id(key: str) -> int | None:
    entry = CATEGORIES.get(key)
    return entry[0] if entry else None


def category_name_vn(key: str) -> str | None:
    entry = CATEGORIES.get(key)
    return entry[1] if entry else None


def is_valid_category(key: str) -> bool:
    return key in CATEGORIES


__all__ = ["CATEGORIES", "category_id", "category_name_vn", "is_valid_category"]
