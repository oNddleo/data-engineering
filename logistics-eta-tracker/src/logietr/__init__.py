"""logistics-eta-tracker — VN shipment ETA + SLA monitor."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Breach": ("logietr.sla", "Breach"),
        "BreachKind": ("logietr.sla", "BreachKind"),
        "Carrier": ("logietr.schema", "Carrier"),
        "CarrierScorecard": ("logietr.leaderboard", "CarrierScorecard"),
        "ETAPrediction": ("logietr.eta", "ETAPrediction"),
        "LaneStats": ("logietr.eta", "LaneStats"),
        "Shipment": ("logietr.schema", "Shipment"),
        "ShipmentState": ("logietr.schema", "ShipmentState"),
        "ShipmentStatus": ("logietr.tracker", "ShipmentStatus"),
        "TERMINAL_STATES": ("logietr.schema", "TERMINAL_STATES"),
        "TrackingEvent": ("logietr.schema", "TrackingEvent"),
        "VN_TZ": ("logietr.schema", "VN_TZ"),
        "apply_events": ("logietr.tracker", "apply_events"),
        "build_lane_stats": ("logietr.eta", "build_lane_stats"),
        "carrier_scorecards": ("logietr.leaderboard", "carrier_scorecards"),
        "dump_events": ("logietr.io_jsonl", "dump_events"),
        "dump_shipments": ("logietr.io_jsonl", "dump_shipments"),
        "event_from_dict": ("logietr.io_jsonl", "event_from_dict"),
        "event_to_dict": ("logietr.io_jsonl", "event_to_dict"),
        "find_overdue": ("logietr.sla", "find_overdue"),
        "find_stuck": ("logietr.sla", "find_stuck"),
        "generate": ("logietr.simulator", "generate"),
        "is_legal_transition": ("logietr.schema", "is_legal_transition"),
        "lane_key": ("logietr.schema", "lane_key"),
        "load_events": ("logietr.io_jsonl", "load_events"),
        "load_shipments": ("logietr.io_jsonl", "load_shipments"),
        "predict_eta": ("logietr.eta", "predict_eta"),
        "rank_by_on_time": ("logietr.leaderboard", "rank_by_on_time"),
        "shipment_from_dict": ("logietr.io_jsonl", "shipment_from_dict"),
        "shipment_to_dict": ("logietr.io_jsonl", "shipment_to_dict"),
        "state_distribution": ("logietr.tracker", "state_distribution"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TERMINAL_STATES",
    "VN_TZ",
    "Breach",
    "BreachKind",
    "Carrier",
    "CarrierScorecard",
    "ETAPrediction",
    "LaneStats",
    "Shipment",
    "ShipmentState",
    "ShipmentStatus",
    "TrackingEvent",
    "__version__",
    "apply_events",
    "build_lane_stats",
    "carrier_scorecards",
    "dump_events",
    "dump_shipments",
    "event_from_dict",
    "event_to_dict",
    "find_overdue",
    "find_stuck",
    "generate",
    "is_legal_transition",
    "lane_key",
    "load_events",
    "load_shipments",
    "predict_eta",
    "rank_by_on_time",
    "shipment_from_dict",
    "shipment_to_dict",
    "state_distribution",
]
