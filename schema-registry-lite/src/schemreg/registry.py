"""Schema registry with versioning and compatibility enforcement.

A "schema" here is represented as a dict[str, str] mapping field names to
type names (e.g. {"id": "int", "name": "str"}).  This is deliberately
simple — no deep JSON Schema — but covers the real patterns:

  BACKWARD: new schema can read data written by old schema
            → only add optional fields (new fields must not be required)
  FORWARD:  old schema can read data written by new schema
            → only remove optional fields (i.e., don't add required fields)
  FULL:     both BACKWARD and FORWARD (no field changes at all, or only
            adding/removing optional markers)
  NONE:     no compatibility enforcement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CompatibilityMode(str, Enum):
    NONE = "NONE"
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    FULL = "FULL"


class CompatibilityError(Exception):
    pass


# A schema is a mapping: field_name -> type_name
# Fields prefixed with "?" are optional, e.g. "?description" -> "str"
Schema = dict[str, str]


def _required_fields(schema: Schema) -> frozenset[str]:
    return frozenset(k for k in schema if not k.startswith("?"))


def _all_fields(schema: Schema) -> frozenset[str]:
    return frozenset(k.lstrip("?") for k in schema)


def _check_backward(old: Schema, new: Schema) -> list[str]:
    """New schema can read old data.  Old required fields must still exist in new."""
    errors: list[str] = []
    for field_name in _required_fields(old):
        bare = field_name.lstrip("?")
        if bare not in _all_fields(new):
            errors.append(f"BACKWARD: required field '{bare}' removed from new schema")
    return errors


def _check_forward(old: Schema, new: Schema) -> list[str]:
    """Old schema can read new data.  New required fields must exist in old."""
    errors: list[str] = []
    for field_name in _required_fields(new):
        bare = field_name.lstrip("?")
        if bare not in _all_fields(old):
            errors.append(f"FORWARD: new required field '{bare}' not in old schema")
    return errors


def check_compatibility(old: Schema, new: Schema, mode: CompatibilityMode) -> list[str]:
    """Return a (possibly empty) list of compatibility violation messages."""
    if mode == CompatibilityMode.NONE:
        return []
    errors: list[str] = []
    if mode in (CompatibilityMode.BACKWARD, CompatibilityMode.FULL):
        errors.extend(_check_backward(old, new))
    if mode in (CompatibilityMode.FORWARD, CompatibilityMode.FULL):
        errors.extend(_check_forward(old, new))
    return errors


@dataclass(frozen=True, slots=True)
class SchemaEntry:
    subject: str
    version: int
    schema: Schema
    created_at_ms: int

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("subject must be non-empty")
        if self.version < 1:
            raise ValueError("version must be >= 1")


@dataclass
class SchemaRegistry:
    """In-memory schema registry."""

    mode: CompatibilityMode = CompatibilityMode.BACKWARD
    _subjects: dict[str, list[SchemaEntry]] = field(default_factory=dict, init=False)

    def register(self, subject: str, schema: Schema, now_ms: int = 0) -> SchemaEntry:
        """Register a new schema version.  Raises CompatibilityError if incompatible."""
        history = self._subjects.get(subject, [])
        if history:
            latest = history[-1]
            errors = check_compatibility(latest.schema, schema, self.mode)
            if errors:
                raise CompatibilityError(
                    f"Schema incompatible with {subject} v{latest.version}: " + "; ".join(errors)
                )
        version = len(history) + 1
        entry = SchemaEntry(
            subject=subject,
            version=version,
            schema=dict(schema),
            created_at_ms=now_ms,
        )
        if subject not in self._subjects:
            self._subjects[subject] = []
        self._subjects[subject].append(entry)
        return entry

    def latest(self, subject: str) -> SchemaEntry:
        history = self._subjects.get(subject)
        if not history:
            raise KeyError(f"Subject not found: {subject}")
        return history[-1]

    def get_version(self, subject: str, version: int) -> SchemaEntry:
        history = self._subjects.get(subject)
        if not history:
            raise KeyError(f"Subject not found: {subject}")
        if version < 1 or version > len(history):
            raise KeyError(f"Version {version} not found for {subject}")
        return history[version - 1]

    def list_subjects(self) -> list[str]:
        return sorted(self._subjects)

    def list_versions(self, subject: str) -> list[int]:
        history = self._subjects.get(subject, [])
        return [e.version for e in history]
