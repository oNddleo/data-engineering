"""abandoned-cart-recovery-pipeline — funnel sessionize + detect + schedule + attribute."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "AbandonReason": ("cartrec.detect", "AbandonReason"),
        "AbandonedSession": ("cartrec.detect", "AbandonedSession"),
        "AttributedTouch": ("cartrec.attribute", "AttributedTouch"),
        "AttributionVerdict": ("cartrec.attribute", "AttributionVerdict"),
        "CampaignTouch": ("cartrec.schema", "CampaignTouch"),
        "DEFAULT_CADENCE": ("cartrec.campaign", "DEFAULT_CADENCE"),
        "Event": ("cartrec.schema", "Event"),
        "EventKind": ("cartrec.schema", "EventKind"),
        "Session": ("cartrec.schema", "Session"),
        "TouchChannel": ("cartrec.schema", "TouchChannel"),
        "VN_TZ": ("cartrec.schema", "VN_TZ"),
        "abandon_rate": ("cartrec.detect", "abandon_rate"),
        "attribute": ("cartrec.attribute", "attribute"),
        "attributed_from_dict": ("cartrec.io_jsonl", "attributed_from_dict"),
        "attributed_to_dict": ("cartrec.io_jsonl", "attributed_to_dict"),
        "conversion_by_channel": ("cartrec.attribute", "conversion_by_channel"),
        "conversion_rate": ("cartrec.attribute", "conversion_rate"),
        "dump_attributed": ("cartrec.io_jsonl", "dump_attributed"),
        "dump_events": ("cartrec.io_jsonl", "dump_events"),
        "dump_sessions": ("cartrec.io_jsonl", "dump_sessions"),
        "dump_touches": ("cartrec.io_jsonl", "dump_touches"),
        "event_from_dict": ("cartrec.io_jsonl", "event_from_dict"),
        "event_to_dict": ("cartrec.io_jsonl", "event_to_dict"),
        "filter_due": ("cartrec.campaign", "filter_due"),
        "find_abandoned": ("cartrec.detect", "find_abandoned"),
        "generate": ("cartrec.simulator", "generate"),
        "load_attributed": ("cartrec.io_jsonl", "load_attributed"),
        "load_events": ("cartrec.io_jsonl", "load_events"),
        "load_sessions": ("cartrec.io_jsonl", "load_sessions"),
        "load_touches": ("cartrec.io_jsonl", "load_touches"),
        "schedule": ("cartrec.campaign", "schedule"),
        "session_from_dict": ("cartrec.io_jsonl", "session_from_dict"),
        "session_to_dict": ("cartrec.io_jsonl", "session_to_dict"),
        "sessionize": ("cartrec.sessionize", "sessionize"),
        "touch_from_dict": ("cartrec.io_jsonl", "touch_from_dict"),
        "touch_to_dict": ("cartrec.io_jsonl", "touch_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_CADENCE",
    "VN_TZ",
    "AbandonReason",
    "AbandonedSession",
    "AttributedTouch",
    "AttributionVerdict",
    "CampaignTouch",
    "Event",
    "EventKind",
    "Session",
    "TouchChannel",
    "__version__",
    "abandon_rate",
    "attribute",
    "attributed_from_dict",
    "attributed_to_dict",
    "conversion_by_channel",
    "conversion_rate",
    "dump_attributed",
    "dump_events",
    "dump_sessions",
    "dump_touches",
    "event_from_dict",
    "event_to_dict",
    "filter_due",
    "find_abandoned",
    "generate",
    "load_attributed",
    "load_events",
    "load_sessions",
    "load_touches",
    "schedule",
    "session_from_dict",
    "session_to_dict",
    "sessionize",
    "touch_from_dict",
    "touch_to_dict",
]
