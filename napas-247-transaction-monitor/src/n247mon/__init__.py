"""napas-247-transaction-monitor — anomaly detection on the NAPAS 247 rail."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Alert": ("n247mon.alerts", "Alert"),
        "AlertKind": ("n247mon.alerts", "AlertKind"),
        "BIN_TO_BANK": ("n247mon.banks", "BIN_TO_BANK"),
        "BiometricRule": ("n247mon.rules", "BiometricRule"),
        "BlacklistRule": ("n247mon.rules", "BlacklistRule"),
        "Channel": ("n247mon.schema", "Channel"),
        "EngineStats": ("n247mon.engine", "EngineStats"),
        "MonitorEngine": ("n247mon.engine", "MonitorEngine"),
        "Rule": ("n247mon.rules", "Rule"),
        "Severity": ("n247mon.alerts", "Severity"),
        "StructuringRule": ("n247mon.rules", "StructuringRule"),
        "Transaction": ("n247mon.schema", "Transaction"),
        "VN_TZ": ("n247mon.schema", "VN_TZ"),
        "VelocityRule": ("n247mon.rules", "VelocityRule"),
        "alert_from_dict": ("n247mon.io_jsonl", "alert_from_dict"),
        "alert_to_dict": ("n247mon.io_jsonl", "alert_to_dict"),
        "bank_name": ("n247mon.banks", "bank_name"),
        "dump_alerts": ("n247mon.io_jsonl", "dump_alerts"),
        "dump_txns": ("n247mon.io_jsonl", "dump_txns"),
        "generate": ("n247mon.simulator", "generate"),
        "is_valid_bin": ("n247mon.banks", "is_valid_bin"),
        "load_alerts": ("n247mon.io_jsonl", "load_alerts"),
        "load_txns": ("n247mon.io_jsonl", "load_txns"),
        "txn_from_dict": ("n247mon.io_jsonl", "txn_from_dict"),
        "txn_to_dict": ("n247mon.io_jsonl", "txn_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BIN_TO_BANK",
    "VN_TZ",
    "Alert",
    "AlertKind",
    "BiometricRule",
    "BlacklistRule",
    "Channel",
    "EngineStats",
    "MonitorEngine",
    "Rule",
    "Severity",
    "StructuringRule",
    "Transaction",
    "VelocityRule",
    "__version__",
    "alert_from_dict",
    "alert_to_dict",
    "bank_name",
    "dump_alerts",
    "dump_txns",
    "generate",
    "is_valid_bin",
    "load_alerts",
    "load_txns",
    "txn_from_dict",
    "txn_to_dict",
]
