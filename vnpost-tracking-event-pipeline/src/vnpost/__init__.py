"""vnpost-tracking-event-pipeline — VN courier tracking pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnpost.couriers import (
        CourierProfile,
        all_profiles,
        profile,
        sla_hours,
    )
    from vnpost.fraud import (
        FraudFinding,
        FraudKind,
        find_abnormal_dwell,
        find_scan_skipping,
    )
    from vnpost.hubs import Hub, all_hubs, by_city, by_code, gateways
    from vnpost.io_jsonl import (
        dump_events,
        dump_frauds,
        dump_parcels,
        dump_slas,
        event_from_dict,
        event_to_dict,
        fraud_from_dict,
        fraud_to_dict,
        load_events,
        load_frauds,
        load_parcels,
        load_slas,
        parcel_from_dict,
        parcel_to_dict,
        sla_from_dict,
        sla_to_dict,
    )
    from vnpost.schema import (
        VN_TZ,
        CourierCode,
        CourierSLA,
        Parcel,
        ParcelEvent,
        ParcelEventKind,
        ParcelStatus,
    )
    from vnpost.simulator import generate
    from vnpost.sla import compute_sla, hours_in_tet_block
    from vnpost.state import stitch, validate


_LAZY: dict[str, tuple[str, str]] = {
    "CourierCode": ("vnpost.schema", "CourierCode"),
    "CourierProfile": ("vnpost.couriers", "CourierProfile"),
    "CourierSLA": ("vnpost.schema", "CourierSLA"),
    "FraudFinding": ("vnpost.fraud", "FraudFinding"),
    "FraudKind": ("vnpost.fraud", "FraudKind"),
    "Hub": ("vnpost.hubs", "Hub"),
    "Parcel": ("vnpost.schema", "Parcel"),
    "ParcelEvent": ("vnpost.schema", "ParcelEvent"),
    "ParcelEventKind": ("vnpost.schema", "ParcelEventKind"),
    "ParcelStatus": ("vnpost.schema", "ParcelStatus"),
    "VN_TZ": ("vnpost.schema", "VN_TZ"),
    "all_hubs": ("vnpost.hubs", "all_hubs"),
    "all_profiles": ("vnpost.couriers", "all_profiles"),
    "by_city": ("vnpost.hubs", "by_city"),
    "by_code": ("vnpost.hubs", "by_code"),
    "compute_sla": ("vnpost.sla", "compute_sla"),
    "dump_events": ("vnpost.io_jsonl", "dump_events"),
    "dump_frauds": ("vnpost.io_jsonl", "dump_frauds"),
    "dump_parcels": ("vnpost.io_jsonl", "dump_parcels"),
    "dump_slas": ("vnpost.io_jsonl", "dump_slas"),
    "event_from_dict": ("vnpost.io_jsonl", "event_from_dict"),
    "event_to_dict": ("vnpost.io_jsonl", "event_to_dict"),
    "find_abnormal_dwell": ("vnpost.fraud", "find_abnormal_dwell"),
    "find_scan_skipping": ("vnpost.fraud", "find_scan_skipping"),
    "fraud_from_dict": ("vnpost.io_jsonl", "fraud_from_dict"),
    "fraud_to_dict": ("vnpost.io_jsonl", "fraud_to_dict"),
    "gateways": ("vnpost.hubs", "gateways"),
    "generate": ("vnpost.simulator", "generate"),
    "hours_in_tet_block": ("vnpost.sla", "hours_in_tet_block"),
    "load_events": ("vnpost.io_jsonl", "load_events"),
    "load_frauds": ("vnpost.io_jsonl", "load_frauds"),
    "load_parcels": ("vnpost.io_jsonl", "load_parcels"),
    "load_slas": ("vnpost.io_jsonl", "load_slas"),
    "parcel_from_dict": ("vnpost.io_jsonl", "parcel_from_dict"),
    "parcel_to_dict": ("vnpost.io_jsonl", "parcel_to_dict"),
    "profile": ("vnpost.couriers", "profile"),
    "sla_from_dict": ("vnpost.io_jsonl", "sla_from_dict"),
    "sla_hours": ("vnpost.couriers", "sla_hours"),
    "sla_to_dict": ("vnpost.io_jsonl", "sla_to_dict"),
    "stitch": ("vnpost.state", "stitch"),
    "validate": ("vnpost.state", "validate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CourierCode",
    "CourierProfile",
    "CourierSLA",
    "FraudFinding",
    "FraudKind",
    "Hub",
    "Parcel",
    "ParcelEvent",
    "ParcelEventKind",
    "ParcelStatus",
    "VN_TZ",
    "__version__",
    "all_hubs",
    "all_profiles",
    "by_city",
    "by_code",
    "compute_sla",
    "dump_events",
    "dump_frauds",
    "dump_parcels",
    "dump_slas",
    "event_from_dict",
    "event_to_dict",
    "find_abnormal_dwell",
    "find_scan_skipping",
    "fraud_from_dict",
    "fraud_to_dict",
    "gateways",
    "generate",
    "hours_in_tet_block",
    "load_events",
    "load_frauds",
    "load_parcels",
    "load_slas",
    "parcel_from_dict",
    "parcel_to_dict",
    "profile",
    "sla_from_dict",
    "sla_hours",
    "sla_to_dict",
    "stitch",
    "validate",
]
