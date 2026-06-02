"""sbv-circular-2345-compliance-pipeline — hash-chained audit ledger for Decision 2345 events."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "AuditEvent": ("sbv2345.schema", "AuditEvent"),
        "AuditLedger": ("sbv2345.ledger", "AuditLedger"),
        "AuthMethod": ("sbv2345.schema", "AuthMethod"),
        "BiometricMethod": ("sbv2345.schema", "BiometricMethod"),
        "Channel": ("sbv2345.schema", "Channel"),
        "Classifier": ("sbv2345.triggers", "Classifier"),
        "DAILY_CUMULATIVE_THRESHOLD": ("sbv2345.triggers", "DAILY_CUMULATIVE_THRESHOLD"),
        "DailySeal": ("sbv2345.ledger", "DailySeal"),
        "EMPTY_ROOT": ("sbv2345.merkle", "EMPTY_ROOT"),
        "LEGAL_BASIS": ("sbv2345.triggers", "LEGAL_BASIS"),
        "REGULATOR_CSV_COLUMNS": ("sbv2345.reports", "REGULATOR_CSV_COLUMNS"),
        "RETENTION_YEARS": ("sbv2345.retention", "RETENTION_YEARS"),
        "ReportSummary": ("sbv2345.reports", "ReportSummary"),
        "RetentionStatus": ("sbv2345.retention", "RetentionStatus"),
        "RetentionSummary": ("sbv2345.retention", "RetentionSummary"),
        "SINGLE_TXN_THRESHOLD": ("sbv2345.triggers", "SINGLE_TXN_THRESHOLD"),
        "SealedAuditRecord": ("sbv2345.ledger", "SealedAuditRecord"),
        "TamperDetected": ("sbv2345.ledger", "TamperDetected"),
        "TransactionEvent": ("sbv2345.schema", "TransactionEvent"),
        "TriggerKind": ("sbv2345.schema", "TriggerKind"),
        "VN_TZ": ("sbv2345.schema", "VN_TZ"),
        "archive_candidates": ("sbv2345.retention", "archive_candidates"),
        "dump_ledger": ("sbv2345.io_jsonl", "dump_ledger"),
        "dump_txns": ("sbv2345.io_jsonl", "dump_txns"),
        "generate": ("sbv2345.simulator", "generate"),
        "hash_pair": ("sbv2345.merkle", "hash_pair"),
        "load_ledger": ("sbv2345.io_jsonl", "load_ledger"),
        "load_txns": ("sbv2345.io_jsonl", "load_txns"),
        "merkle_root": ("sbv2345.merkle", "merkle_root"),
        "record_from_dict": ("sbv2345.io_jsonl", "record_from_dict"),
        "record_to_dict": ("sbv2345.io_jsonl", "record_to_dict"),
        "regulator_csv": ("sbv2345.reports", "regulator_csv"),
        "retention_cutoff": ("sbv2345.retention", "retention_cutoff"),
        "retention_summarise": ("sbv2345.retention", "summarise"),
        "status": ("sbv2345.retention", "status"),
        "summarise_report": ("sbv2345.reports", "summarise"),
        "txn_from_dict": ("sbv2345.io_jsonl", "txn_from_dict"),
        "txn_to_dict": ("sbv2345.io_jsonl", "txn_to_dict"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DAILY_CUMULATIVE_THRESHOLD",
    "EMPTY_ROOT",
    "LEGAL_BASIS",
    "REGULATOR_CSV_COLUMNS",
    "RETENTION_YEARS",
    "SINGLE_TXN_THRESHOLD",
    "VN_TZ",
    "AuditEvent",
    "AuditLedger",
    "AuthMethod",
    "BiometricMethod",
    "Channel",
    "Classifier",
    "DailySeal",
    "ReportSummary",
    "RetentionStatus",
    "RetentionSummary",
    "SealedAuditRecord",
    "TamperDetected",
    "TransactionEvent",
    "TriggerKind",
    "__version__",
    "archive_candidates",
    "dump_ledger",
    "dump_txns",
    "generate",
    "hash_pair",
    "load_ledger",
    "load_txns",
    "merkle_root",
    "record_from_dict",
    "record_to_dict",
    "regulator_csv",
    "retention_cutoff",
    "retention_summarise",
    "status",
    "summarise_report",
    "txn_from_dict",
    "txn_to_dict",
]
