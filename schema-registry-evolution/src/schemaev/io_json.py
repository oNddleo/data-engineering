"""JSON codec for Schema + Field + CompatibilityReport.

The on-disk format is a flat JSON object that's hand-editable and
diffs cleanly in PRs — not a binary or compact form.
"""

from __future__ import annotations

import json

from schemaev.schema import (
    Compatibility,
    CompatibilityReport,
    Field,
    FieldChange,
    FieldType,
    Schema,
)


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str | null, got {type(v).__name__}")
    return v


def field_to_dict(f: Field) -> dict[str, object]:
    return {
        "name": f.name,
        "type": f.type.value,
        "required": f.required,
        "default": f.default,
        "aliases": list(f.aliases),
    }


def field_from_dict(d: dict[str, object]) -> Field:
    raw_aliases = d.get("aliases", [])
    if not isinstance(raw_aliases, list):
        raise TypeError("aliases must be a list")
    aliases = tuple(a for a in raw_aliases if isinstance(a, str))
    return Field(
        name=_require_str(d, "name"),
        type=FieldType(_require_str(d, "type")),
        required=_require_bool(d, "required") if "required" in d else True,
        default=_optional_str(d, "default"),
        aliases=aliases,
    )


def schema_to_dict(s: Schema) -> dict[str, object]:
    return {
        "name": s.name,
        "version": s.version,
        "fields": [field_to_dict(f) for f in s.fields],
    }


def schema_from_dict(d: dict[str, object]) -> Schema:
    raw_fields = d.get("fields")
    if not isinstance(raw_fields, list):
        raise TypeError("fields must be a list")
    fields = tuple(field_from_dict(f) for f in raw_fields if isinstance(f, dict))
    return Schema(
        name=_require_str(d, "name"),
        version=_require_str(d, "version"),
        fields=fields,
    )


def schema_to_json(s: Schema) -> str:
    return json.dumps(schema_to_dict(s), indent=2, ensure_ascii=False)


def schema_from_json(text: str) -> Schema:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError("schema must be a JSON object")
    return schema_from_dict(parsed)


def change_to_dict(c: FieldChange) -> dict[str, object]:
    return {
        "kind": c.kind,
        "field_name": c.field_name,
        "old": field_to_dict(c.old) if c.old is not None else None,
        "new": field_to_dict(c.new) if c.new is not None else None,
        "detail": c.detail,
    }


def report_to_dict(r: CompatibilityReport) -> dict[str, object]:
    return {
        "mode": r.mode.value,
        "is_compatible": r.is_compatible,
        "breaking_changes": [change_to_dict(c) for c in r.breaking_changes],
        "safe_changes": [change_to_dict(c) for c in r.safe_changes],
    }


def report_to_json(r: CompatibilityReport) -> str:
    return json.dumps(report_to_dict(r), indent=2, ensure_ascii=False)


def parse_compatibility(name: str) -> Compatibility:
    """Convenience: case-insensitive map to the Compatibility enum."""
    try:
        return Compatibility(name.upper())
    except ValueError as exc:
        raise ValueError(
            f"unknown compatibility mode {name!r}; "
            f"choose from {[c.value for c in Compatibility]}"
        ) from exc


__all__ = [
    "change_to_dict",
    "field_from_dict",
    "field_to_dict",
    "parse_compatibility",
    "report_to_dict",
    "report_to_json",
    "schema_from_dict",
    "schema_from_json",
    "schema_to_dict",
    "schema_to_json",
]
