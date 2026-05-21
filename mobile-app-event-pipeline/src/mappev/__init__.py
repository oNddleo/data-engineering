"""mobile-app-event-pipeline — attribution + cohort + LTV + fraud."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Attribution": ("mappev.schema", "Attribution"),
        "CohortLTV": ("mappev.schema", "CohortLTV"),
        "CohortRetention": ("mappev.schema", "CohortRetention"),
        "Event": ("mappev.schema", "Event"),
        "EventKind": ("mappev.schema", "EventKind"),
        "FraudFinding": ("mappev.fraud", "FraudFinding"),
        "FraudKind": ("mappev.fraud", "FraudKind"),
        "VN_TZ": ("mappev.schema", "VN_TZ"),
        "attribute": ("mappev.attribute", "attribute"),
        "attribution_from_dict": ("mappev.io_jsonl", "attribution_from_dict"),
        "attribution_to_dict": ("mappev.io_jsonl", "attribution_to_dict"),
        "dump_attributions": ("mappev.io_jsonl", "dump_attributions"),
        "dump_events": ("mappev.io_jsonl", "dump_events"),
        "dump_frauds": ("mappev.io_jsonl", "dump_frauds"),
        "dump_ltvs": ("mappev.io_jsonl", "dump_ltvs"),
        "dump_retentions": ("mappev.io_jsonl", "dump_retentions"),
        "event_from_dict": ("mappev.io_jsonl", "event_from_dict"),
        "event_to_dict": ("mappev.io_jsonl", "event_to_dict"),
        "find_click_injection": ("mappev.fraud", "find_click_injection"),
        "find_install_spam": ("mappev.fraud", "find_install_spam"),
        "fraud_from_dict": ("mappev.io_jsonl", "fraud_from_dict"),
        "fraud_to_dict": ("mappev.io_jsonl", "fraud_to_dict"),
        "generate": ("mappev.simulator", "generate"),
        "load_attributions": ("mappev.io_jsonl", "load_attributions"),
        "load_events": ("mappev.io_jsonl", "load_events"),
        "load_frauds": ("mappev.io_jsonl", "load_frauds"),
        "load_ltvs": ("mappev.io_jsonl", "load_ltvs"),
        "load_retentions": ("mappev.io_jsonl", "load_retentions"),
        "ltv": ("mappev.cohort", "ltv"),
        "ltv_from_dict": ("mappev.io_jsonl", "ltv_from_dict"),
        "ltv_to_dict": ("mappev.io_jsonl", "ltv_to_dict"),
        "retention": ("mappev.cohort", "retention"),
        "retention_from_dict": ("mappev.io_jsonl", "retention_from_dict"),
        "retention_to_dict": ("mappev.io_jsonl", "retention_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Attribution",
    "CohortLTV",
    "CohortRetention",
    "Event",
    "EventKind",
    "FraudFinding",
    "FraudKind",
    "VN_TZ",
    "__version__",
    "attribute",
    "attribution_from_dict",
    "attribution_to_dict",
    "dump_attributions",
    "dump_events",
    "dump_frauds",
    "dump_ltvs",
    "dump_retentions",
    "event_from_dict",
    "event_to_dict",
    "find_click_injection",
    "find_install_spam",
    "fraud_from_dict",
    "fraud_to_dict",
    "generate",
    "load_attributions",
    "load_events",
    "load_frauds",
    "load_ltvs",
    "load_retentions",
    "ltv",
    "ltv_from_dict",
    "ltv_to_dict",
    "retention",
    "retention_from_dict",
    "retention_to_dict",
]
