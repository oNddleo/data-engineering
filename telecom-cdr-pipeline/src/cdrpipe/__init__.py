"""telecom-cdr-pipeline — VN telecom CDR rating, billing, fraud detection."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "CDR": ("cdrpipe.schema", "CDR"),
        "CDRKind": ("cdrpipe.schema", "CDRKind"),
        "Carrier": ("cdrpipe.schema", "Carrier"),
        "CarrierProfile": ("cdrpipe.carriers", "CarrierProfile"),
        "DEFAULT_TARIFF": ("cdrpipe.rating", "DEFAULT_TARIFF"),
        "FraudFinding": ("cdrpipe.fraud", "FraudFinding"),
        "FraudKind": ("cdrpipe.fraud", "FraudKind"),
        "MonthlyBill": ("cdrpipe.schema", "MonthlyBill"),
        "PlanKind": ("cdrpipe.schema", "PlanKind"),
        "RatedCDR": ("cdrpipe.schema", "RatedCDR"),
        "TariffTable": ("cdrpipe.rating", "TariffTable"),
        "VN_TZ": ("cdrpipe.schema", "VN_TZ"),
        "aggregate_bills": ("cdrpipe.billing", "aggregate_bills"),
        "all_profiles": ("cdrpipe.carriers", "all_profiles"),
        "bill_from_dict": ("cdrpipe.io_jsonl", "bill_from_dict"),
        "bill_to_dict": ("cdrpipe.io_jsonl", "bill_to_dict"),
        "billable_minutes": ("cdrpipe.rating", "billable_minutes"),
        "carrier_for": ("cdrpipe.carriers", "carrier_for"),
        "cdr_from_dict": ("cdrpipe.io_jsonl", "cdr_from_dict"),
        "cdr_to_dict": ("cdrpipe.io_jsonl", "cdr_to_dict"),
        "dump_bills": ("cdrpipe.io_jsonl", "dump_bills"),
        "dump_cdrs": ("cdrpipe.io_jsonl", "dump_cdrs"),
        "dump_frauds": ("cdrpipe.io_jsonl", "dump_frauds"),
        "dump_rated": ("cdrpipe.io_jsonl", "dump_rated"),
        "find_foreign_roaming": ("cdrpipe.fraud", "find_foreign_roaming"),
        "find_premium_rate_spikes": ("cdrpipe.fraud", "find_premium_rate_spikes"),
        "find_sim_swap": ("cdrpipe.fraud", "find_sim_swap"),
        "fraud_from_dict": ("cdrpipe.io_jsonl", "fraud_from_dict"),
        "fraud_to_dict": ("cdrpipe.io_jsonl", "fraud_to_dict"),
        "generate": ("cdrpipe.simulator", "generate"),
        "is_peak": ("cdrpipe.rating", "is_peak"),
        "is_premium_msisdn": ("cdrpipe.carriers", "is_premium_msisdn"),
        "load_bills": ("cdrpipe.io_jsonl", "load_bills"),
        "load_cdrs": ("cdrpipe.io_jsonl", "load_cdrs"),
        "load_frauds": ("cdrpipe.io_jsonl", "load_frauds"),
        "load_rated": ("cdrpipe.io_jsonl", "load_rated"),
        "normalise_msisdn": ("cdrpipe.carriers", "normalise_msisdn"),
        "profile_for": ("cdrpipe.carriers", "profile_for"),
        "rate": ("cdrpipe.rating", "rate"),
        "rated_from_dict": ("cdrpipe.io_jsonl", "rated_from_dict"),
        "rated_to_dict": ("cdrpipe.io_jsonl", "rated_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CDR",
    "CDRKind",
    "Carrier",
    "CarrierProfile",
    "DEFAULT_TARIFF",
    "FraudFinding",
    "FraudKind",
    "MonthlyBill",
    "PlanKind",
    "RatedCDR",
    "TariffTable",
    "VN_TZ",
    "__version__",
    "aggregate_bills",
    "all_profiles",
    "bill_from_dict",
    "bill_to_dict",
    "billable_minutes",
    "carrier_for",
    "cdr_from_dict",
    "cdr_to_dict",
    "dump_bills",
    "dump_cdrs",
    "dump_frauds",
    "dump_rated",
    "find_foreign_roaming",
    "find_premium_rate_spikes",
    "find_sim_swap",
    "fraud_from_dict",
    "fraud_to_dict",
    "generate",
    "is_peak",
    "is_premium_msisdn",
    "load_bills",
    "load_cdrs",
    "load_frauds",
    "load_rated",
    "normalise_msisdn",
    "profile_for",
    "rate",
    "rated_from_dict",
    "rated_to_dict",
]
