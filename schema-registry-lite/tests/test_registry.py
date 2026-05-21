"""Unit tests for schema registry."""

from __future__ import annotations

import pytest

from schemreg.registry import (
    CompatibilityError,
    CompatibilityMode,
    SchemaRegistry,
    check_compatibility,
)

S1: dict[str, str] = {"id": "int", "name": "str"}
S2_ADDOPT: dict[str, str] = {"id": "int", "name": "str", "?email": "str"}  # add optional
S2_ADDREQ: dict[str, str] = {"id": "int", "name": "str", "phone": "str"}  # add required
S2_REMOVE: dict[str, str] = {"id": "int"}  # remove required field


class TestCompatibilityCheck:
    def test_none_always_compatible(self) -> None:
        assert check_compatibility(S1, S2_ADDREQ, CompatibilityMode.NONE) == []
        assert check_compatibility(S1, S2_REMOVE, CompatibilityMode.NONE) == []

    def test_backward_add_optional_ok(self) -> None:
        assert check_compatibility(S1, S2_ADDOPT, CompatibilityMode.BACKWARD) == []

    def test_backward_remove_required_fails(self) -> None:
        errors = check_compatibility(S1, S2_REMOVE, CompatibilityMode.BACKWARD)
        assert errors  # "name" removed

    def test_backward_add_required_ok(self) -> None:
        # Adding required field doesn't break BACKWARD (old data can't produce it,
        # but the new schema can still read old data; this is a design choice here)
        assert check_compatibility(S1, S2_ADDREQ, CompatibilityMode.BACKWARD) == []

    def test_forward_add_required_fails(self) -> None:
        errors = check_compatibility(S1, S2_ADDREQ, CompatibilityMode.FORWARD)
        assert errors  # "phone" is new required field

    def test_forward_add_optional_ok(self) -> None:
        assert check_compatibility(S1, S2_ADDOPT, CompatibilityMode.FORWARD) == []

    def test_forward_remove_required_ok(self) -> None:
        assert check_compatibility(S1, S2_REMOVE, CompatibilityMode.FORWARD) == []

    def test_full_add_optional_ok(self) -> None:
        assert check_compatibility(S1, S2_ADDOPT, CompatibilityMode.FULL) == []

    def test_full_remove_required_fails(self) -> None:
        errors = check_compatibility(S1, S2_REMOVE, CompatibilityMode.FULL)
        assert errors

    def test_full_add_required_fails(self) -> None:
        errors = check_compatibility(S1, S2_ADDREQ, CompatibilityMode.FULL)
        assert errors


class TestRegistry:
    def test_first_registration_version_1(self) -> None:
        reg = SchemaRegistry()
        entry = reg.register("topic", S1)
        assert entry.version == 1
        assert entry.subject == "topic"

    def test_sequential_versions(self) -> None:
        reg = SchemaRegistry(mode=CompatibilityMode.NONE)
        reg.register("t", S1)
        reg.register("t", S2_ADDREQ)
        assert reg.list_versions("t") == [1, 2]

    def test_latest_returns_newest(self) -> None:
        reg = SchemaRegistry(mode=CompatibilityMode.NONE)
        reg.register("t", S1)
        reg.register("t", S2_ADDREQ)
        assert reg.latest("t").version == 2

    def test_get_version_by_number(self) -> None:
        reg = SchemaRegistry(mode=CompatibilityMode.NONE)
        reg.register("t", S1)
        reg.register("t", S2_ADDREQ)
        e = reg.get_version("t", 1)
        assert e.schema == S1

    def test_compatibility_enforced_on_register(self) -> None:
        reg = SchemaRegistry(mode=CompatibilityMode.BACKWARD)
        reg.register("t", S1)
        with pytest.raises(CompatibilityError):
            reg.register("t", S2_REMOVE)

    def test_latest_unknown_subject_raises(self) -> None:
        reg = SchemaRegistry()
        with pytest.raises(KeyError):
            reg.latest("unknown")

    def test_get_version_out_of_range_raises(self) -> None:
        reg = SchemaRegistry()
        reg.register("t", S1)
        with pytest.raises(KeyError):
            reg.get_version("t", 99)

    def test_list_subjects(self) -> None:
        reg = SchemaRegistry()
        reg.register("b", S1)
        reg.register("a", S1)
        assert reg.list_subjects() == ["a", "b"]

    def test_multiple_subjects_independent(self) -> None:
        reg = SchemaRegistry(mode=CompatibilityMode.BACKWARD)
        reg.register("orders", S1)
        reg.register("users", S1)
        # Each subject starts at v1
        assert reg.latest("orders").version == 1
        assert reg.latest("users").version == 1


class TestSchemaEntryValidation:
    def test_empty_subject_raises(self) -> None:
        from schemreg.registry import SchemaEntry

        with pytest.raises(ValueError):
            SchemaEntry(subject="", version=1, schema={}, created_at_ms=0)

    def test_zero_version_raises(self) -> None:
        from schemreg.registry import SchemaEntry

        with pytest.raises(ValueError):
            SchemaEntry(subject="t", version=0, schema={}, created_at_ms=0)
