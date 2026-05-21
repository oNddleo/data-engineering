"""shopee-product-scraper-warehouse — Shopee VN warehouse + aggregations."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "CATEGORIES": ("shopeedw.categories", "CATEGORIES"),
        "CategoryStats": ("shopeedw.aggregations", "CategoryStats"),
        "MockShopeeScraper": ("shopeedw.scraper", "MockShopeeScraper"),
        "PriceDrop": ("shopeedw.aggregations", "PriceDrop"),
        "PriceHistory": ("shopeedw.warehouse", "PriceHistory"),
        "ProductFacts": ("shopeedw.warehouse", "ProductFacts"),
        "SellerRanking": ("shopeedw.aggregations", "SellerRanking"),
        "ShopFacts": ("shopeedw.warehouse", "ShopFacts"),
        "ShopeeNotFoundError": ("shopeedw.scraper", "ShopeeNotFoundError"),
        "ShopeeProduct": ("shopeedw.schema", "ShopeeProduct"),
        "ShopeeScraper": ("shopeedw.scraper", "ShopeeScraper"),
        "ShopeeShop": ("shopeedw.schema", "ShopeeShop"),
        "VN_TZ": ("shopeedw.schema", "VN_TZ"),
        "Warehouse": ("shopeedw.warehouse", "Warehouse"),
        "WarehouseSummary": ("shopeedw.aggregations", "WarehouseSummary"),
        "category_breakdown": ("shopeedw.aggregations", "category_breakdown"),
        "category_id": ("shopeedw.categories", "category_id"),
        "category_name_vn": ("shopeedw.categories", "category_name_vn"),
        "dump_products": ("shopeedw.io_jsonl", "dump_products"),
        "dump_shops": ("shopeedw.io_jsonl", "dump_shops"),
        "generate": ("shopeedw.simulator", "generate"),
        "is_valid_category": ("shopeedw.categories", "is_valid_category"),
        "load_products": ("shopeedw.io_jsonl", "load_products"),
        "load_shops": ("shopeedw.io_jsonl", "load_shops"),
        "price_drops": ("shopeedw.aggregations", "price_drops"),
        "product_from_dict": ("shopeedw.io_jsonl", "product_from_dict"),
        "product_to_dict": ("shopeedw.io_jsonl", "product_to_dict"),
        "shop_from_dict": ("shopeedw.io_jsonl", "shop_from_dict"),
        "shop_to_dict": ("shopeedw.io_jsonl", "shop_to_dict"),
        "summarise": ("shopeedw.aggregations", "summarise"),
        "top_categories_by_gmv": ("shopeedw.aggregations", "top_categories_by_gmv"),
        "top_sellers_by_gmv": ("shopeedw.aggregations", "top_sellers_by_gmv"),
        "top_sellers_by_volume": ("shopeedw.aggregations", "top_sellers_by_volume"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CATEGORIES",
    "VN_TZ",
    "CategoryStats",
    "MockShopeeScraper",
    "PriceDrop",
    "PriceHistory",
    "ProductFacts",
    "SellerRanking",
    "ShopFacts",
    "ShopeeNotFoundError",
    "ShopeeProduct",
    "ShopeeScraper",
    "ShopeeShop",
    "Warehouse",
    "WarehouseSummary",
    "__version__",
    "category_breakdown",
    "category_id",
    "category_name_vn",
    "dump_products",
    "dump_shops",
    "generate",
    "is_valid_category",
    "load_products",
    "load_shops",
    "price_drops",
    "product_from_dict",
    "product_to_dict",
    "shop_from_dict",
    "shop_to_dict",
    "summarise",
    "top_categories_by_gmv",
    "top_sellers_by_gmv",
    "top_sellers_by_volume",
]
