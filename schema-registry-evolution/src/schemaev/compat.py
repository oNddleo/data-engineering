"""Compatibility rules — BACKWARD / FORWARD / FULL / NONE.

The Confluent Schema Registry taxonomy (which every Kafka + Pulsar
deployment uses):

| Mode      | Meaning                                                       |
| --------- | ------------------------------------------------------------- |
| NONE      | No checks.                                                    |
| BACKWARD  | New schema can read data written by old schema.               |
| FORWARD   | Old schema can read data written by new schema.               |
| FULL      | Both BACKWARD and FORWARD.                                    |

BACKWARD-compatible changes (new schema can read old data):

* Adding a field **with a default**.
* Removing an optional field.
* Adding an alias to a renamed field.
* Widening a type (int → long, float → double, etc.).

BACKWARD-breaking changes:

* Adding a required field without default.
* Removing a required field.
* Changing a type incompatibly (string → int, bool → string, …).

FORWARD-compatible changes (old schema can read new data):

* Removing a field with a default.
* Adding an optional field.
* Narrowing a type (long → int — if data fits).

FORWARD-breaking: most of the above with directions reversed.

The toolkit implements a **conservative** set: any change whose
safety depends on data values (e.g. long → int when "data fits")
is treated as breaking. Production callers who know their data
override on a case-by-case basis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from schemaev.diff import diff
from schemaev.schema import Compatibility, CompatibilityReport, FieldChange, FieldType

if TYPE_CHECKING:
    from schemaev.schema import Schema


# Promotion graph — ``(src, dst)`` is a safe widening if dst can hold any src value.
_BACKWARD_SAFE_PROMOTIONS: frozenset[tuple[FieldType, FieldType]] = frozenset(
    {
        (FieldType.INT, FieldType.LONG),
        (FieldType.INT, FieldType.FLOAT),
        (FieldType.INT, FieldType.DOUBLE),
        (FieldType.LONG, FieldType.FLOAT),
        (FieldType.LONG, FieldType.DOUBLE),
        (FieldType.FLOAT, FieldType.DOUBLE),
        (FieldType.STRING, FieldType.BYTES),
        (FieldType.BYTES, FieldType.STRING),
    }
)


def _is_backward_safe_type_change(src: FieldType, dst: FieldType) -> bool:
    """``True`` if writing ``src`` and reading as ``dst`` is data-safe."""
    if src == dst:
        return True
    return (src, dst) in _BACKWARD_SAFE_PROMOTIONS


def _is_forward_safe_type_change(src: FieldType, dst: FieldType) -> bool:
    """Forward safety is the reverse direction."""
    if src == dst:
        return True
    # Forward = old schema reads new data, so old schema reads as ``src``
    # while data is written as ``dst``. Safe if dst is a promotion of src.
    return (dst, src) in _BACKWARD_SAFE_PROMOTIONS


def _classify_backward(change: FieldChange) -> bool:
    """``True`` if the change is BACKWARD-compatible (new schema reads old data)."""
    if change.kind == "ADDED":
        # New schema sees a field that old data won't have → must have default.
        assert change.new is not None
        return change.new.default is not None or not change.new.required
    if change.kind == "REMOVED":
        # New schema dropped a field that old data still has → safe (ignore extra).
        return True
    if change.kind == "TYPE_CHANGED":
        assert change.old is not None and change.new is not None
        return _is_backward_safe_type_change(change.old.type, change.new.type)
    if change.kind == "REQUIRED_CHANGED":
        # Going from required → optional is safe (new schema is more permissive).
        # Going from optional → required is NOT safe (new reader rejects old data).
        assert change.old is not None and change.new is not None
        return change.old.required and not change.new.required
    if change.kind == "DEFAULT_CHANGED":
        # Default-only changes are BACKWARD-safe — the wire format hasn't moved.
        return True
    # ALIAS_ADDED lets the new schema accept the old name → safe.
    return change.kind == "ALIAS_ADDED"


def _classify_forward(change: FieldChange) -> bool:
    """``True`` if the change is FORWARD-compatible (old schema reads new data)."""
    if change.kind == "ADDED":
        # Old schema doesn't know about the new field → ignored on read. Safe.
        return True
    if change.kind == "REMOVED":
        # Old schema expects the field → must have had a default to be safe.
        assert change.old is not None
        return change.old.default is not None or not change.old.required
    if change.kind == "TYPE_CHANGED":
        assert change.old is not None and change.new is not None
        return _is_forward_safe_type_change(change.old.type, change.new.type)
    if change.kind == "REQUIRED_CHANGED":
        # Forward: old schema reads data written by new. If new is required
        # but old is optional, old reader sees the value — safe.
        # If new is optional but old is required, old reader expects a value
        # that may be missing — unsafe.
        assert change.old is not None and change.new is not None
        return change.old.required or change.new.required
    if change.kind == "DEFAULT_CHANGED":
        return True
    return change.kind == "ALIAS_ADDED"


def check_backward(old: Schema, new: Schema) -> CompatibilityReport:
    """Can the **new** schema read data written by the **old** schema?"""
    changes = diff(old, new)
    safe: list[FieldChange] = []
    breaking: list[FieldChange] = []
    for c in changes:
        if _classify_backward(c):
            safe.append(c)
        else:
            breaking.append(c)
    return CompatibilityReport(
        mode=Compatibility.BACKWARD,
        is_compatible=not breaking,
        breaking_changes=tuple(breaking),
        safe_changes=tuple(safe),
    )


def check_forward(old: Schema, new: Schema) -> CompatibilityReport:
    """Can the **old** schema read data written by the **new** schema?"""
    changes = diff(old, new)
    safe: list[FieldChange] = []
    breaking: list[FieldChange] = []
    for c in changes:
        if _classify_forward(c):
            safe.append(c)
        else:
            breaking.append(c)
    return CompatibilityReport(
        mode=Compatibility.FORWARD,
        is_compatible=not breaking,
        breaking_changes=tuple(breaking),
        safe_changes=tuple(safe),
    )


def check_full(old: Schema, new: Schema) -> CompatibilityReport:
    """Both BACKWARD and FORWARD compatible."""
    b = check_backward(old, new)
    f = check_forward(old, new)
    breaking = tuple(b.breaking_changes) + tuple(
        c for c in f.breaking_changes if c not in b.breaking_changes
    )
    safe = tuple(c for c in b.safe_changes if c in f.safe_changes)
    return CompatibilityReport(
        mode=Compatibility.FULL,
        is_compatible=not breaking,
        breaking_changes=breaking,
        safe_changes=safe,
    )


def check(old: Schema, new: Schema, mode: Compatibility) -> CompatibilityReport:
    """Dispatch to the appropriate compatibility checker."""
    if mode is Compatibility.NONE:
        return CompatibilityReport(mode=Compatibility.NONE, is_compatible=True)
    if mode is Compatibility.BACKWARD:
        return check_backward(old, new)
    if mode is Compatibility.FORWARD:
        return check_forward(old, new)
    return check_full(old, new)


__all__ = ["check", "check_backward", "check_forward", "check_full"]
