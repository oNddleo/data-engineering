"""schema-registry-evolution — diff + BACKWARD/FORWARD/FULL compat + semver bump."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "BumpKind": ("schemaev.versioning", "BumpKind"),
        "Compatibility": ("schemaev.schema", "Compatibility"),
        "CompatibilityReport": ("schemaev.schema", "CompatibilityReport"),
        "Field": ("schemaev.schema", "Field"),
        "FieldChange": ("schemaev.schema", "FieldChange"),
        "FieldType": ("schemaev.schema", "FieldType"),
        "Schema": ("schemaev.schema", "Schema"),
        "all_mutations": ("schemaev.simulator", "all_mutations"),
        "change_to_dict": ("schemaev.io_json", "change_to_dict"),
        "check": ("schemaev.compat", "check"),
        "check_backward": ("schemaev.compat", "check_backward"),
        "check_forward": ("schemaev.compat", "check_forward"),
        "check_full": ("schemaev.compat", "check_full"),
        "diff": ("schemaev.diff", "diff"),
        "field_from_dict": ("schemaev.io_json", "field_from_dict"),
        "field_to_dict": ("schemaev.io_json", "field_to_dict"),
        "generate_pair": ("schemaev.simulator", "generate_pair"),
        "next_version": ("schemaev.versioning", "next_version"),
        "parse_compatibility": ("schemaev.io_json", "parse_compatibility"),
        "parse_semver": ("schemaev.versioning", "parse_semver"),
        "render_semver": ("schemaev.versioning", "render_semver"),
        "report_to_dict": ("schemaev.io_json", "report_to_dict"),
        "report_to_json": ("schemaev.io_json", "report_to_json"),
        "schema_from_dict": ("schemaev.io_json", "schema_from_dict"),
        "schema_from_json": ("schemaev.io_json", "schema_from_json"),
        "schema_to_dict": ("schemaev.io_json", "schema_to_dict"),
        "schema_to_json": ("schemaev.io_json", "schema_to_json"),
        "suggest_bump": ("schemaev.versioning", "suggest_bump"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BumpKind",
    "Compatibility",
    "CompatibilityReport",
    "Field",
    "FieldChange",
    "FieldType",
    "Schema",
    "__version__",
    "all_mutations",
    "change_to_dict",
    "check",
    "check_backward",
    "check_forward",
    "check_full",
    "diff",
    "field_from_dict",
    "field_to_dict",
    "generate_pair",
    "next_version",
    "parse_compatibility",
    "parse_semver",
    "render_semver",
    "report_to_dict",
    "report_to_json",
    "schema_from_dict",
    "schema_from_json",
    "schema_to_dict",
    "schema_to_json",
    "suggest_bump",
]
