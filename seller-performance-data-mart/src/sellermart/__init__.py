"""seller-performance-data-mart — star-schema VN seller KPIs."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "DailyTrend": ("sellermart.kpis", "DailyTrend"),
        "DimCategory": ("sellermart.schema", "DimCategory"),
        "DimDate": ("sellermart.schema", "DimDate"),
        "DimSeller": ("sellermart.schema", "DimSeller"),
        "FactSellerDay": ("sellermart.schema", "FactSellerDay"),
        "Order": ("sellermart.sources", "Order"),
        "Return": ("sellermart.sources", "Return"),
        "Review": ("sellermart.sources", "Review"),
        "SellerSummary": ("sellermart.kpis", "SellerSummary"),
        "VN_TZ": ("sellermart.schema", "VN_TZ"),
        "build_fact_seller_day": ("sellermart.etl", "build_fact_seller_day"),
        "daily_trend": ("sellermart.kpis", "daily_trend"),
        "dump_facts": ("sellermart.io_jsonl", "dump_facts"),
        "dump_orders": ("sellermart.io_jsonl", "dump_orders"),
        "dump_returns": ("sellermart.io_jsonl", "dump_returns"),
        "dump_reviews": ("sellermart.io_jsonl", "dump_reviews"),
        "fact_from_dict": ("sellermart.io_jsonl", "fact_from_dict"),
        "fact_to_dict": ("sellermart.io_jsonl", "fact_to_dict"),
        "generate": ("sellermart.simulator", "generate"),
        "load_facts": ("sellermart.io_jsonl", "load_facts"),
        "load_orders": ("sellermart.io_jsonl", "load_orders"),
        "load_returns": ("sellermart.io_jsonl", "load_returns"),
        "load_reviews": ("sellermart.io_jsonl", "load_reviews"),
        "make_date_key": ("sellermart.schema", "make_date_key"),
        "make_dim_date": ("sellermart.schema", "make_dim_date"),
        "order_from_dict": ("sellermart.io_jsonl", "order_from_dict"),
        "order_to_dict": ("sellermart.io_jsonl", "order_to_dict"),
        "return_from_dict": ("sellermart.io_jsonl", "return_from_dict"),
        "return_to_dict": ("sellermart.io_jsonl", "return_to_dict"),
        "review_from_dict": ("sellermart.io_jsonl", "review_from_dict"),
        "review_to_dict": ("sellermart.io_jsonl", "review_to_dict"),
        "seller_summary": ("sellermart.kpis", "seller_summary"),
        "top_sellers_by_gmv": ("sellermart.kpis", "top_sellers_by_gmv"),
        "worst_sellers_by_return_rate": ("sellermart.kpis", "worst_sellers_by_return_rate"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VN_TZ",
    "DailyTrend",
    "DimCategory",
    "DimDate",
    "DimSeller",
    "FactSellerDay",
    "Order",
    "Return",
    "Review",
    "SellerSummary",
    "__version__",
    "build_fact_seller_day",
    "daily_trend",
    "dump_facts",
    "dump_orders",
    "dump_returns",
    "dump_reviews",
    "fact_from_dict",
    "fact_to_dict",
    "generate",
    "load_facts",
    "load_orders",
    "load_returns",
    "load_reviews",
    "make_date_key",
    "make_dim_date",
    "order_from_dict",
    "order_to_dict",
    "return_from_dict",
    "return_to_dict",
    "review_from_dict",
    "review_to_dict",
    "seller_summary",
    "top_sellers_by_gmv",
    "worst_sellers_by_return_rate",
]
