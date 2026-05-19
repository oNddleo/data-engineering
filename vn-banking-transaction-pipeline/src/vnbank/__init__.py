"""vn-banking-transaction-pipeline — VN domestic banking + AML toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnbank.aml import (
        AMLFinding,
        AMLKind,
        find_ctr,
        find_high_velocity,
        find_structuring,
    )
    from vnbank.banks import (
        BankProfile,
        all_profiles,
        is_valid_account,
        profile_for_abbr,
        profile_for_bin,
    )
    from vnbank.io_jsonl import (
        aml_from_dict,
        aml_to_dict,
        dump_amls,
        dump_summaries,
        dump_txns,
        load_amls,
        load_summaries,
        load_txns,
        summary_from_dict,
        summary_to_dict,
        txn_from_dict,
        txn_to_dict,
    )
    from vnbank.routing import (
        NAPAS_247_MAX_VND,
        Rail,
        RouteDecision,
        route,
    )
    from vnbank.schema import (
        CTR_THRESHOLD_VND,
        VN_TZ,
        Account,
        Bank,
        DailySummary,
        Transaction,
        TxnDirection,
        TxnKind,
        TxnStatus,
    )
    from vnbank.simulator import generate
    from vnbank.summary import aggregate_daily
    from vnbank.vietqr import (
        VietQRPayload,
        build_vietqr,
        crc16_ccitt,
        parse_vietqr,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "AMLFinding": ("vnbank.aml", "AMLFinding"),
    "AMLKind": ("vnbank.aml", "AMLKind"),
    "Account": ("vnbank.schema", "Account"),
    "Bank": ("vnbank.schema", "Bank"),
    "BankProfile": ("vnbank.banks", "BankProfile"),
    "CTR_THRESHOLD_VND": ("vnbank.schema", "CTR_THRESHOLD_VND"),
    "DailySummary": ("vnbank.schema", "DailySummary"),
    "NAPAS_247_MAX_VND": ("vnbank.routing", "NAPAS_247_MAX_VND"),
    "Rail": ("vnbank.routing", "Rail"),
    "RouteDecision": ("vnbank.routing", "RouteDecision"),
    "Transaction": ("vnbank.schema", "Transaction"),
    "TxnDirection": ("vnbank.schema", "TxnDirection"),
    "TxnKind": ("vnbank.schema", "TxnKind"),
    "TxnStatus": ("vnbank.schema", "TxnStatus"),
    "VN_TZ": ("vnbank.schema", "VN_TZ"),
    "VietQRPayload": ("vnbank.vietqr", "VietQRPayload"),
    "aggregate_daily": ("vnbank.summary", "aggregate_daily"),
    "all_profiles": ("vnbank.banks", "all_profiles"),
    "aml_from_dict": ("vnbank.io_jsonl", "aml_from_dict"),
    "aml_to_dict": ("vnbank.io_jsonl", "aml_to_dict"),
    "build_vietqr": ("vnbank.vietqr", "build_vietqr"),
    "crc16_ccitt": ("vnbank.vietqr", "crc16_ccitt"),
    "dump_amls": ("vnbank.io_jsonl", "dump_amls"),
    "dump_summaries": ("vnbank.io_jsonl", "dump_summaries"),
    "dump_txns": ("vnbank.io_jsonl", "dump_txns"),
    "find_ctr": ("vnbank.aml", "find_ctr"),
    "find_high_velocity": ("vnbank.aml", "find_high_velocity"),
    "find_structuring": ("vnbank.aml", "find_structuring"),
    "generate": ("vnbank.simulator", "generate"),
    "is_valid_account": ("vnbank.banks", "is_valid_account"),
    "load_amls": ("vnbank.io_jsonl", "load_amls"),
    "load_summaries": ("vnbank.io_jsonl", "load_summaries"),
    "load_txns": ("vnbank.io_jsonl", "load_txns"),
    "parse_vietqr": ("vnbank.vietqr", "parse_vietqr"),
    "profile_for_abbr": ("vnbank.banks", "profile_for_abbr"),
    "profile_for_bin": ("vnbank.banks", "profile_for_bin"),
    "route": ("vnbank.routing", "route"),
    "summary_from_dict": ("vnbank.io_jsonl", "summary_from_dict"),
    "summary_to_dict": ("vnbank.io_jsonl", "summary_to_dict"),
    "txn_from_dict": ("vnbank.io_jsonl", "txn_from_dict"),
    "txn_to_dict": ("vnbank.io_jsonl", "txn_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AMLFinding",
    "AMLKind",
    "Account",
    "Bank",
    "BankProfile",
    "CTR_THRESHOLD_VND",
    "DailySummary",
    "NAPAS_247_MAX_VND",
    "Rail",
    "RouteDecision",
    "Transaction",
    "TxnDirection",
    "TxnKind",
    "TxnStatus",
    "VN_TZ",
    "VietQRPayload",
    "__version__",
    "aggregate_daily",
    "all_profiles",
    "aml_from_dict",
    "aml_to_dict",
    "build_vietqr",
    "crc16_ccitt",
    "dump_amls",
    "dump_summaries",
    "dump_txns",
    "find_ctr",
    "find_high_velocity",
    "find_structuring",
    "generate",
    "is_valid_account",
    "load_amls",
    "load_summaries",
    "load_txns",
    "parse_vietqr",
    "profile_for_abbr",
    "profile_for_bin",
    "route",
    "summary_from_dict",
    "summary_to_dict",
    "txn_from_dict",
    "txn_to_dict",
]
