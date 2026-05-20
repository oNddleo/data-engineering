"""vn-ride-hailing-trip-pipeline — Grab / Be / Xanh SM / Maxim trip toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnride.fraud import (
        FraudFinding,
        FraudKind,
        find_cancellation_abuse,
        find_ghost_rides,
        find_surge_gaming,
    )
    from vnride.io_jsonl import (
        dump_frauds,
        dump_settlements,
        dump_trips,
        fare_from_dict,
        fare_to_dict,
        fraud_from_dict,
        fraud_to_dict,
        load_frauds,
        load_settlements,
        load_trips,
        settlement_from_dict,
        settlement_to_dict,
        trip_from_dict,
        trip_to_dict,
    )
    from vnride.operators import (
        CityProfile,
        OperatorProfile,
        all_cities,
        all_operators,
        city_for,
        commission_bps,
        operator_for,
    )
    from vnride.pricing import (
        DEFAULT_TARIFFS,
        MAX_SURGE_BPS,
        MIN_SURGE_BPS,
        Tariff,
        commission_split,
        quote,
    )
    from vnride.schema import (
        VN_TZ,
        CancelledBy,
        DriverSettlement,
        FareBreakdown,
        PaymentMethod,
        ServiceType,
        Trip,
        TripState,
    )
    from vnride.settlement import aggregate_daily
    from vnride.simulator import generate
    from vnride.state_machine import (
        allowed_next,
        is_terminal,
        validate_history,
        validate_transition,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "CancelledBy": ("vnride.schema", "CancelledBy"),
    "CityProfile": ("vnride.operators", "CityProfile"),
    "DEFAULT_TARIFFS": ("vnride.pricing", "DEFAULT_TARIFFS"),
    "DriverSettlement": ("vnride.schema", "DriverSettlement"),
    "FareBreakdown": ("vnride.schema", "FareBreakdown"),
    "FraudFinding": ("vnride.fraud", "FraudFinding"),
    "FraudKind": ("vnride.fraud", "FraudKind"),
    "MAX_SURGE_BPS": ("vnride.pricing", "MAX_SURGE_BPS"),
    "MIN_SURGE_BPS": ("vnride.pricing", "MIN_SURGE_BPS"),
    "OperatorProfile": ("vnride.operators", "OperatorProfile"),
    "PaymentMethod": ("vnride.schema", "PaymentMethod"),
    "ServiceType": ("vnride.schema", "ServiceType"),
    "Tariff": ("vnride.pricing", "Tariff"),
    "Trip": ("vnride.schema", "Trip"),
    "TripState": ("vnride.schema", "TripState"),
    "VN_TZ": ("vnride.schema", "VN_TZ"),
    "aggregate_daily": ("vnride.settlement", "aggregate_daily"),
    "all_cities": ("vnride.operators", "all_cities"),
    "all_operators": ("vnride.operators", "all_operators"),
    "allowed_next": ("vnride.state_machine", "allowed_next"),
    "city_for": ("vnride.operators", "city_for"),
    "commission_bps": ("vnride.operators", "commission_bps"),
    "commission_split": ("vnride.pricing", "commission_split"),
    "dump_frauds": ("vnride.io_jsonl", "dump_frauds"),
    "dump_settlements": ("vnride.io_jsonl", "dump_settlements"),
    "dump_trips": ("vnride.io_jsonl", "dump_trips"),
    "fare_from_dict": ("vnride.io_jsonl", "fare_from_dict"),
    "fare_to_dict": ("vnride.io_jsonl", "fare_to_dict"),
    "find_cancellation_abuse": ("vnride.fraud", "find_cancellation_abuse"),
    "find_ghost_rides": ("vnride.fraud", "find_ghost_rides"),
    "find_surge_gaming": ("vnride.fraud", "find_surge_gaming"),
    "fraud_from_dict": ("vnride.io_jsonl", "fraud_from_dict"),
    "fraud_to_dict": ("vnride.io_jsonl", "fraud_to_dict"),
    "generate": ("vnride.simulator", "generate"),
    "is_terminal": ("vnride.state_machine", "is_terminal"),
    "load_frauds": ("vnride.io_jsonl", "load_frauds"),
    "load_settlements": ("vnride.io_jsonl", "load_settlements"),
    "load_trips": ("vnride.io_jsonl", "load_trips"),
    "operator_for": ("vnride.operators", "operator_for"),
    "quote": ("vnride.pricing", "quote"),
    "settlement_from_dict": ("vnride.io_jsonl", "settlement_from_dict"),
    "settlement_to_dict": ("vnride.io_jsonl", "settlement_to_dict"),
    "trip_from_dict": ("vnride.io_jsonl", "trip_from_dict"),
    "trip_to_dict": ("vnride.io_jsonl", "trip_to_dict"),
    "validate_history": ("vnride.state_machine", "validate_history"),
    "validate_transition": ("vnride.state_machine", "validate_transition"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CancelledBy",
    "CityProfile",
    "DEFAULT_TARIFFS",
    "DriverSettlement",
    "FareBreakdown",
    "FraudFinding",
    "FraudKind",
    "MAX_SURGE_BPS",
    "MIN_SURGE_BPS",
    "OperatorProfile",
    "PaymentMethod",
    "ServiceType",
    "Tariff",
    "Trip",
    "TripState",
    "VN_TZ",
    "__version__",
    "aggregate_daily",
    "all_cities",
    "all_operators",
    "allowed_next",
    "city_for",
    "commission_bps",
    "commission_split",
    "dump_frauds",
    "dump_settlements",
    "dump_trips",
    "fare_from_dict",
    "fare_to_dict",
    "find_cancellation_abuse",
    "find_ghost_rides",
    "find_surge_gaming",
    "fraud_from_dict",
    "fraud_to_dict",
    "generate",
    "is_terminal",
    "load_frauds",
    "load_settlements",
    "load_trips",
    "operator_for",
    "quote",
    "settlement_from_dict",
    "settlement_to_dict",
    "trip_from_dict",
    "trip_to_dict",
    "validate_history",
    "validate_transition",
]
