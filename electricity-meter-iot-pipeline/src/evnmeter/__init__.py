"""electricity-meter-iot-pipeline — EVN smart-meter telemetry pipeline."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Anomaly": ("evnmeter.anomaly", "Anomaly"),
        "AnomalyKind": ("evnmeter.anomaly", "AnomalyKind"),
        "ConsumptionInterval": ("evnmeter.schema", "ConsumptionInterval"),
        "DEFAULT_VAT_BPS": ("evnmeter.tariff", "DEFAULT_VAT_BPS"),
        "METER_MAX_X100": ("evnmeter.schema", "METER_MAX_X100"),
        "Meter": ("evnmeter.schema", "Meter"),
        "MeterKind": ("evnmeter.schema", "MeterKind"),
        "MonthlyBill": ("evnmeter.billing", "MonthlyBill"),
        "Reading": ("evnmeter.schema", "Reading"),
        "TierBreak": ("evnmeter.tariff", "TierBreak"),
        "TierBreakdown": ("evnmeter.tariff", "TierBreakdown"),
        "VN_TZ": ("evnmeter.schema", "VN_TZ"),
        "bill_from_dict": ("evnmeter.io_jsonl", "bill_from_dict"),
        "bill_meters": ("evnmeter.billing", "bill_meters"),
        "bill_to_dict": ("evnmeter.io_jsonl", "bill_to_dict"),
        "compute_bill": ("evnmeter.tariff", "compute_bill"),
        "default_tiers": ("evnmeter.tariff", "default_tiers"),
        "derive": ("evnmeter.derive", "derive"),
        "dump_bills": ("evnmeter.io_jsonl", "dump_bills"),
        "dump_intervals": ("evnmeter.io_jsonl", "dump_intervals"),
        "dump_meters": ("evnmeter.io_jsonl", "dump_meters"),
        "dump_readings": ("evnmeter.io_jsonl", "dump_readings"),
        "find_gaps": ("evnmeter.anomaly", "find_gaps"),
        "find_spikes": ("evnmeter.anomaly", "find_spikes"),
        "find_stuck": ("evnmeter.anomaly", "find_stuck"),
        "generate": ("evnmeter.simulator", "generate"),
        "interval_from_dict": ("evnmeter.io_jsonl", "interval_from_dict"),
        "interval_to_dict": ("evnmeter.io_jsonl", "interval_to_dict"),
        "load_bills": ("evnmeter.io_jsonl", "load_bills"),
        "load_intervals": ("evnmeter.io_jsonl", "load_intervals"),
        "load_meters": ("evnmeter.io_jsonl", "load_meters"),
        "load_readings": ("evnmeter.io_jsonl", "load_readings"),
        "meter_from_dict": ("evnmeter.io_jsonl", "meter_from_dict"),
        "meter_to_dict": ("evnmeter.io_jsonl", "meter_to_dict"),
        "reading_from_dict": ("evnmeter.io_jsonl", "reading_from_dict"),
        "reading_to_dict": ("evnmeter.io_jsonl", "reading_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_VAT_BPS",
    "METER_MAX_X100",
    "VN_TZ",
    "Anomaly",
    "AnomalyKind",
    "ConsumptionInterval",
    "Meter",
    "MeterKind",
    "MonthlyBill",
    "Reading",
    "TierBreak",
    "TierBreakdown",
    "__version__",
    "bill_from_dict",
    "bill_meters",
    "bill_to_dict",
    "compute_bill",
    "default_tiers",
    "derive",
    "dump_bills",
    "dump_intervals",
    "dump_meters",
    "dump_readings",
    "find_gaps",
    "find_spikes",
    "find_stuck",
    "generate",
    "interval_from_dict",
    "interval_to_dict",
    "load_bills",
    "load_intervals",
    "load_meters",
    "load_readings",
    "meter_from_dict",
    "meter_to_dict",
    "reading_from_dict",
    "reading_to_dict",
]
