"""anti-money-laundering-graph — in-memory graph + 5 AML pattern detectors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from amlgraph.alerts import AlertKind, AMLAlert, Severity
    from amlgraph.graph import TransactionGraph
    from amlgraph.io_jsonl import (
        account_from_dict,
        account_to_dict,
        alert_from_dict,
        alert_to_dict,
        dump_accounts,
        dump_alerts,
        dump_txns,
        load_accounts,
        load_alerts,
        load_txns,
        txn_from_dict,
        txn_to_dict,
    )
    from amlgraph.patterns import (
        detect_fan_in,
        detect_fan_out,
        detect_layering_chains,
        detect_round_trips,
        detect_structured_deposits,
    )
    from amlgraph.schema import (
        VN_TZ,
        Account,
        AccountType,
        Channel,
        RiskFlag,
        Transaction,
    )
    from amlgraph.scoring import (
        KIND_MULTIPLIER,
        RISK_FLAG_POINTS,
        SEVERITY_POINTS,
        RankedAccount,
        score_accounts,
        top_n,
    )
    from amlgraph.simulator import generate


_LAZY: dict[str, tuple[str, str]] = {
    "AMLAlert": ("amlgraph.alerts", "AMLAlert"),
    "Account": ("amlgraph.schema", "Account"),
    "AccountType": ("amlgraph.schema", "AccountType"),
    "AlertKind": ("amlgraph.alerts", "AlertKind"),
    "Channel": ("amlgraph.schema", "Channel"),
    "KIND_MULTIPLIER": ("amlgraph.scoring", "KIND_MULTIPLIER"),
    "RISK_FLAG_POINTS": ("amlgraph.scoring", "RISK_FLAG_POINTS"),
    "RankedAccount": ("amlgraph.scoring", "RankedAccount"),
    "RiskFlag": ("amlgraph.schema", "RiskFlag"),
    "SEVERITY_POINTS": ("amlgraph.scoring", "SEVERITY_POINTS"),
    "Severity": ("amlgraph.alerts", "Severity"),
    "Transaction": ("amlgraph.schema", "Transaction"),
    "TransactionGraph": ("amlgraph.graph", "TransactionGraph"),
    "VN_TZ": ("amlgraph.schema", "VN_TZ"),
    "account_from_dict": ("amlgraph.io_jsonl", "account_from_dict"),
    "account_to_dict": ("amlgraph.io_jsonl", "account_to_dict"),
    "alert_from_dict": ("amlgraph.io_jsonl", "alert_from_dict"),
    "alert_to_dict": ("amlgraph.io_jsonl", "alert_to_dict"),
    "detect_fan_in": ("amlgraph.patterns", "detect_fan_in"),
    "detect_fan_out": ("amlgraph.patterns", "detect_fan_out"),
    "detect_layering_chains": ("amlgraph.patterns", "detect_layering_chains"),
    "detect_round_trips": ("amlgraph.patterns", "detect_round_trips"),
    "detect_structured_deposits": ("amlgraph.patterns", "detect_structured_deposits"),
    "dump_accounts": ("amlgraph.io_jsonl", "dump_accounts"),
    "dump_alerts": ("amlgraph.io_jsonl", "dump_alerts"),
    "dump_txns": ("amlgraph.io_jsonl", "dump_txns"),
    "generate": ("amlgraph.simulator", "generate"),
    "load_accounts": ("amlgraph.io_jsonl", "load_accounts"),
    "load_alerts": ("amlgraph.io_jsonl", "load_alerts"),
    "load_txns": ("amlgraph.io_jsonl", "load_txns"),
    "score_accounts": ("amlgraph.scoring", "score_accounts"),
    "top_n": ("amlgraph.scoring", "top_n"),
    "txn_from_dict": ("amlgraph.io_jsonl", "txn_from_dict"),
    "txn_to_dict": ("amlgraph.io_jsonl", "txn_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "KIND_MULTIPLIER",
    "RISK_FLAG_POINTS",
    "SEVERITY_POINTS",
    "VN_TZ",
    "AMLAlert",
    "Account",
    "AccountType",
    "AlertKind",
    "Channel",
    "RankedAccount",
    "RiskFlag",
    "Severity",
    "Transaction",
    "TransactionGraph",
    "__version__",
    "account_from_dict",
    "account_to_dict",
    "alert_from_dict",
    "alert_to_dict",
    "detect_fan_in",
    "detect_fan_out",
    "detect_layering_chains",
    "detect_round_trips",
    "detect_structured_deposits",
    "dump_accounts",
    "dump_alerts",
    "dump_txns",
    "generate",
    "load_accounts",
    "load_alerts",
    "load_txns",
    "score_accounts",
    "top_n",
    "txn_from_dict",
    "txn_to_dict",
]
