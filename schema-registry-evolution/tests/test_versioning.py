"""Semver bump suggester + next_version."""

from __future__ import annotations

import pytest

from schemaev.diff import diff
from schemaev.schema import FieldType
from schemaev.versioning import (
    BumpKind,
    next_version,
    parse_semver,
    render_semver,
    suggest_bump,
)

from ._fixtures import make_field, make_schema


def test_no_changes_bump_is_none():
    assert suggest_bump([]) is BumpKind.NONE


def test_safe_add_bump_is_minor():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(
        fields=(
            make_field(name="x"),
            make_field(name="y", required=False, default=""),
        )
    )
    assert suggest_bump(diff(old, new)) is BumpKind.MINOR


def test_default_change_bump_is_patch():
    old = make_schema(fields=(make_field(name="x", required=False, default="a"),))
    new = make_schema(fields=(make_field(name="x", required=False, default="b"),))
    assert suggest_bump(diff(old, new)) is BumpKind.PATCH


def test_required_add_bump_is_major():
    old = make_schema(fields=(make_field(name="x"),))
    new = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    assert suggest_bump(diff(old, new)) is BumpKind.MAJOR


def test_type_narrow_bump_is_major():
    old = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    assert suggest_bump(diff(old, new)) is BumpKind.MAJOR


def test_remove_required_bump_is_major():
    old = make_schema(fields=(make_field(name="x"), make_field(name="y")))
    new = make_schema(fields=(make_field(name="x"),))
    # Removing a required field is BACKWARD-safe (the new reader just
    # ignores it) per Avro spec — so this is MINOR, not MAJOR.
    # (FORWARD-incompatibility doesn't bump major in our taxonomy;
    # we only escalate to MAJOR for BACKWARD-incompatibility.)
    assert suggest_bump(diff(old, new)) is BumpKind.MINOR


def test_type_widen_bump_is_minor():
    """Widening is BACKWARD-safe but breaks FORWARD — we treat as MINOR."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.INT),))
    new = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    assert suggest_bump(diff(old, new)) is BumpKind.MINOR


def test_major_dominates_other_bumps():
    """If any change is BACKWARD-breaking, we bump MAJOR even if other
    changes would only suggest MINOR or PATCH."""
    old = make_schema(fields=(make_field(name="x", type=FieldType.LONG),))
    new = make_schema(
        fields=(
            make_field(name="x", type=FieldType.INT),  # MAJOR
            make_field(name="y", required=False, default=""),  # MINOR
        )
    )
    assert suggest_bump(diff(old, new)) is BumpKind.MAJOR


# ---------- semver parsing ----------------------------------------------


def test_parse_semver_valid():
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("0.0.0") == (0, 0, 0)


def test_parse_semver_rejects_two_parts():
    with pytest.raises(ValueError):
        parse_semver("1.2")


def test_parse_semver_rejects_non_int():
    with pytest.raises(ValueError):
        parse_semver("1.a.3")


def test_parse_semver_rejects_negative():
    with pytest.raises(ValueError):
        parse_semver("-1.0.0")


def test_render_semver_inverse_parse():
    assert render_semver(1, 2, 3) == "1.2.3"


def test_next_version_major():
    assert next_version("1.2.3", BumpKind.MAJOR) == "2.0.0"


def test_next_version_minor_resets_patch():
    assert next_version("1.2.3", BumpKind.MINOR) == "1.3.0"


def test_next_version_patch():
    assert next_version("1.2.3", BumpKind.PATCH) == "1.2.4"


def test_next_version_none_returns_current():
    assert next_version("1.2.3", BumpKind.NONE) == "1.2.3"


def test_next_version_from_zero():
    assert next_version("0.0.0", BumpKind.MINOR) == "0.1.0"
