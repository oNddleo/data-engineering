"""Schema model — a deliberately-minimal subset of JSON Schema / Avro.

We model only what affects **wire compatibility** for streaming
formats (Avro, Protobuf, JSON Schema). That means:

* **Field name** — the key downstream parsers use.
* **Field type** — string / int / long / float / double / bool /
  bytes / nullable variants.
* **Required vs optional** — Avro `union [null, T]` or JSON Schema
  `required: []` membership.
* **Default value** — only fields with defaults can be safely added
  to an existing schema (FORWARD compat).
* **Aliases** — Avro's mechanism for renaming fields without
  breaking older readers.

Things we deliberately don't model:

* Nested records (modelled as a flat namespace — production callers
  flatten before feeding the diff).
* Logical types (decimal, timestamp-millis) — these are wire-
  compatible with their underlying primitive type, so we treat them
  as the primitive.
* Doc strings, namespaces, doc fields — these don't affect compat.

Field-type promotion rules (Avro 1.11 spec):

| From   | Compatible To                |
| ------ | ---------------------------- |
| int    | int, long, float, double     |
| long   | long, float, double          |
| float  | float, double                |
| double | double                       |
| string | string, bytes                |
| bytes  | bytes, string                |

Other type transitions break compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldType(str, Enum):
    """Wire-level primitive types we model."""

    STRING = "STRING"
    INT = "INT"
    LONG = "LONG"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    BOOL = "BOOL"
    BYTES = "BYTES"


class Compatibility(str, Enum):
    """Confluent-style compatibility modes."""

    NONE = "NONE"  # No check.
    BACKWARD = "BACKWARD"  # New schema can read old data.
    FORWARD = "FORWARD"  # Old schema can read new data.
    FULL = "FULL"  # Both BACKWARD and FORWARD.


@dataclass(frozen=True, slots=True)
class Field:
    """One field in a schema.

    ``required=True`` and ``default=None`` together mean **no default**.
    ``required=False`` with ``default=None`` means the field is nullable
    with no default — the reader can decide what to do.
    """

    name: str
    type: FieldType
    required: bool = True
    default: str | None = None  # serialised default (kept as string to skip parsing)
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.name.replace("_", "").isalnum():
            raise ValueError(f"name must be alphanumeric/underscore, got {self.name!r}")
        if self.required and self.default is None:
            # Legal: required with no default. The reader must see this
            # field in every record.
            pass
        for alias in self.aliases:
            if not alias or not alias.replace("_", "").isalnum():
                raise ValueError(f"alias {alias!r} must be alphanumeric/underscore")


@dataclass(frozen=True, slots=True)
class Schema:
    """A flat record schema with ordered fields."""

    name: str
    version: str  # semver-ish; not parsed at this layer
    fields: tuple[Field, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.version:
            raise ValueError("version must be non-empty")
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate field names in schema: {names}")

    def field_named(self, name: str) -> Field | None:
        """Look up a field by name or alias."""
        for f in self.fields:
            if f.name == name or name in f.aliases:
                return f
        return None


@dataclass(frozen=True, slots=True)
class FieldChange:
    """One change between two schema versions.

    ``kind`` is one of:

    * ``ADDED`` — field present in new but not old.
    * ``REMOVED`` — field present in old but not new.
    * ``TYPE_CHANGED`` — same name, different type.
    * ``REQUIRED_CHANGED`` — required flag flipped (either direction).
    * ``DEFAULT_CHANGED`` — default value changed.
    * ``ALIAS_ADDED`` — alias appeared.
    """

    kind: str
    field_name: str
    old: Field | None
    new: Field | None
    detail: str = ""

    def __post_init__(self) -> None:
        valid_kinds = {
            "ADDED",
            "REMOVED",
            "TYPE_CHANGED",
            "REQUIRED_CHANGED",
            "DEFAULT_CHANGED",
            "ALIAS_ADDED",
        }
        if self.kind not in valid_kinds:
            raise ValueError(f"kind must be one of {valid_kinds}, got {self.kind!r}")
        if not self.field_name:
            raise ValueError("field_name must be non-empty")


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Outcome of a compatibility check."""

    mode: Compatibility
    is_compatible: bool
    breaking_changes: tuple[FieldChange, ...] = field(default_factory=tuple)
    safe_changes: tuple[FieldChange, ...] = field(default_factory=tuple)


__all__ = [
    "Compatibility",
    "CompatibilityReport",
    "Field",
    "FieldChange",
    "FieldType",
    "Schema",
]
