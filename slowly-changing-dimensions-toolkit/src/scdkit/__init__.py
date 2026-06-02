"""slowly-changing-dimensions-toolkit — Kimball SCD Type 1/2/3/4/6."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "ChangeKind": ("scdkit.schema", "ChangeKind"),
        "DimensionChange": ("scdkit.schema", "DimensionChange"),
        "DimensionRow": ("scdkit.schema", "DimensionRow"),
        "HIGH_DATE": ("scdkit.schema", "HIGH_DATE"),
        "SCDType": ("scdkit.schema", "SCDType"),
        "Type2State": ("scdkit.appliers", "Type2State"),
        "Type4State": ("scdkit.appliers", "Type4State"),
        "Type6State": ("scdkit.appliers", "Type6State"),
        "VN_TZ": ("scdkit.schema", "VN_TZ"),
        "apply_type_1": ("scdkit.appliers", "apply_type_1"),
        "apply_type_2": ("scdkit.appliers", "apply_type_2"),
        "apply_type_3": ("scdkit.appliers", "apply_type_3"),
        "apply_type_4": ("scdkit.appliers", "apply_type_4"),
        "apply_type_6": ("scdkit.appliers", "apply_type_6"),
        "change_from_dict": ("scdkit.io_jsonl", "change_from_dict"),
        "change_to_dict": ("scdkit.io_jsonl", "change_to_dict"),
        "detect": ("scdkit.detect", "detect"),
        "dump_changes": ("scdkit.io_jsonl", "dump_changes"),
        "dump_rows": ("scdkit.io_jsonl", "dump_rows"),
        "generate_pair": ("scdkit.simulator", "generate_pair"),
        "load_changes": ("scdkit.io_jsonl", "load_changes"),
        "load_rows": ("scdkit.io_jsonl", "load_rows"),
        "n_changes_by_kind": ("scdkit.detect", "n_changes_by_kind"),
        "row_from_dict": ("scdkit.io_jsonl", "row_from_dict"),
        "row_to_dict": ("scdkit.io_jsonl", "row_to_dict"),
        "snapshot_from_text": ("scdkit.io_jsonl", "snapshot_from_text"),
        "snapshot_to_lines": ("scdkit.io_jsonl", "snapshot_to_lines"),
        "type_2_current": ("scdkit.appliers", "type_2_current"),
        "type_2_empty": ("scdkit.appliers", "type_2_empty"),
        "type_2_history_for": ("scdkit.appliers", "type_2_history_for"),
        "type_4_empty": ("scdkit.appliers", "type_4_empty"),
        "type_6_empty": ("scdkit.appliers", "type_6_empty"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "HIGH_DATE",
    "VN_TZ",
    "ChangeKind",
    "DimensionChange",
    "DimensionRow",
    "SCDType",
    "Type2State",
    "Type4State",
    "Type6State",
    "__version__",
    "apply_type_1",
    "apply_type_2",
    "apply_type_3",
    "apply_type_4",
    "apply_type_6",
    "change_from_dict",
    "change_to_dict",
    "detect",
    "dump_changes",
    "dump_rows",
    "generate_pair",
    "load_changes",
    "load_rows",
    "n_changes_by_kind",
    "row_from_dict",
    "row_to_dict",
    "snapshot_from_text",
    "snapshot_to_lines",
    "type_2_current",
    "type_2_empty",
    "type_2_history_for",
    "type_4_empty",
    "type_6_empty",
]
