"""customer-lifetime-value-segmenter — RFM + segment + CLV pipeline."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "CLVForecast": ("clvseg.clv", "CLVForecast"),
        "Customer": ("clvseg.schema", "Customer"),
        "Order": ("clvseg.schema", "Order"),
        "RFMScore": ("clvseg.schema", "RFMScore"),
        "Segment": ("clvseg.schema", "Segment"),
        "VN_TZ": ("clvseg.schema", "VN_TZ"),
        "classify_all": ("clvseg.segments", "classify_all"),
        "clv_from_dict": ("clvseg.io_jsonl", "clv_from_dict"),
        "clv_to_dict": ("clvseg.io_jsonl", "clv_to_dict"),
        "customer_from_dict": ("clvseg.io_jsonl", "customer_from_dict"),
        "customer_to_dict": ("clvseg.io_jsonl", "customer_to_dict"),
        "dump_clvs": ("clvseg.io_jsonl", "dump_clvs"),
        "dump_customers": ("clvseg.io_jsonl", "dump_customers"),
        "dump_orders": ("clvseg.io_jsonl", "dump_orders"),
        "dump_scores": ("clvseg.io_jsonl", "dump_scores"),
        "forecast": ("clvseg.clv", "forecast"),
        "generate": ("clvseg.simulator", "generate"),
        "load_clvs": ("clvseg.io_jsonl", "load_clvs"),
        "load_customers": ("clvseg.io_jsonl", "load_customers"),
        "load_orders": ("clvseg.io_jsonl", "load_orders"),
        "load_scores": ("clvseg.io_jsonl", "load_scores"),
        "order_from_dict": ("clvseg.io_jsonl", "order_from_dict"),
        "order_to_dict": ("clvseg.io_jsonl", "order_to_dict"),
        "rfm_to_segment": ("clvseg.segments", "rfm_to_segment"),
        "score": ("clvseg.rfm", "score"),
        "score_from_dict": ("clvseg.io_jsonl", "score_from_dict"),
        "score_to_dict": ("clvseg.io_jsonl", "score_to_dict"),
        "segment_distribution": ("clvseg.segments", "segment_distribution"),
        "top_clv": ("clvseg.clv", "top_clv"),
        "top_in_segment": ("clvseg.segments", "top_in_segment"),
        "total_clv_by_segment": ("clvseg.clv", "total_clv_by_segment"),
        "transitions": ("clvseg.segments", "transitions"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VN_TZ",
    "CLVForecast",
    "Customer",
    "Order",
    "RFMScore",
    "Segment",
    "__version__",
    "classify_all",
    "clv_from_dict",
    "clv_to_dict",
    "customer_from_dict",
    "customer_to_dict",
    "dump_clvs",
    "dump_customers",
    "dump_orders",
    "dump_scores",
    "forecast",
    "generate",
    "load_clvs",
    "load_customers",
    "load_orders",
    "load_scores",
    "order_from_dict",
    "order_to_dict",
    "rfm_to_segment",
    "score",
    "score_from_dict",
    "score_to_dict",
    "segment_distribution",
    "top_clv",
    "top_in_segment",
    "total_clv_by_segment",
    "transitions",
]
