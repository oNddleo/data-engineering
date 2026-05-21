"""dwh-data-quality-toolkit — composable VN-aware data quality framework."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "Check": ("dqkit.schema", "Check"),
        "CheckResult": ("dqkit.schema", "CheckResult"),
        "CheckSpec": ("dqkit.schema", "CheckSpec"),
        "FailedRow": ("dqkit.schema", "FailedRow"),
        "Row": ("dqkit.schema", "Row"),
        "Severity": ("dqkit.schema", "Severity"),
        "Suite": ("dqkit.schema", "Suite"),
        "cccd": ("dqkit.checks_vn", "cccd"),
        "dtype_int": ("dqkit.checks_generic", "dtype_int"),
        "dtype_str": ("dqkit.checks_generic", "dtype_str"),
        "dump_results": ("dqkit.io_jsonl", "dump_results"),
        "dump_rows": ("dqkit.io_jsonl", "dump_rows"),
        "generate": ("dqkit.simulator", "generate"),
        "in_set": ("dqkit.checks_generic", "in_set"),
        "list_checks": ("dqkit.runner", "list_checks"),
        "load_results": ("dqkit.io_jsonl", "load_results"),
        "load_rows": ("dqkit.io_jsonl", "load_rows"),
        "mst": ("dqkit.checks_vn", "mst"),
        "not_null": ("dqkit.checks_generic", "not_null"),
        "quarantine_rows": ("dqkit.runner", "quarantine_rows"),
        "range_int": ("dqkit.checks_generic", "range_int"),
        "regex": ("dqkit.checks_generic", "regex"),
        "render_summary": ("dqkit.runner", "render_summary"),
        "result_from_dict": ("dqkit.io_jsonl", "result_from_dict"),
        "result_to_dict": ("dqkit.io_jsonl", "result_to_dict"),
        "run_suite": ("dqkit.runner", "run_suite"),
        "suite_from_json": ("dqkit.io_jsonl", "suite_from_json"),
        "suite_to_json": ("dqkit.io_jsonl", "suite_to_json"),
        "summarise": ("dqkit.runner", "summarise"),
        "unique": ("dqkit.checks_generic", "unique"),
        "vn_bank_account": ("dqkit.checks_vn", "vn_bank_account"),
        "vn_phone": ("dqkit.checks_vn", "vn_phone"),
        "vn_postal_code": ("dqkit.checks_vn", "vn_postal_code"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Check",
    "CheckResult",
    "CheckSpec",
    "FailedRow",
    "Row",
    "Severity",
    "Suite",
    "__version__",
    "cccd",
    "dtype_int",
    "dtype_str",
    "dump_results",
    "dump_rows",
    "generate",
    "in_set",
    "list_checks",
    "load_results",
    "load_rows",
    "mst",
    "not_null",
    "quarantine_rows",
    "range_int",
    "regex",
    "render_summary",
    "result_from_dict",
    "result_to_dict",
    "run_suite",
    "suite_from_json",
    "suite_to_json",
    "summarise",
    "unique",
    "vn_bank_account",
    "vn_phone",
    "vn_postal_code",
]
