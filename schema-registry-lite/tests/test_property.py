"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from schemreg.registry import CompatibilityMode, SchemaRegistry, check_compatibility

_FIELD_NAMES = st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10)
_TYPE_NAMES = st.sampled_from(["int", "str", "float", "bool"])
_SCHEMA = st.dictionaries(_FIELD_NAMES, _TYPE_NAMES, min_size=0, max_size=8)


@given(_SCHEMA)
@settings(max_examples=100)
def test_none_mode_always_compatible(schema: dict[str, str]) -> None:
    errors = check_compatibility(schema, schema, CompatibilityMode.NONE)
    assert errors == []


@given(_SCHEMA)
@settings(max_examples=100)
def test_same_schema_compatible_all_modes(schema: dict[str, str]) -> None:
    for mode in CompatibilityMode:
        errors = check_compatibility(schema, schema, mode)
        assert errors == []


@given(_SCHEMA, _SCHEMA)
@settings(max_examples=100)
def test_register_none_mode_never_raises(s1: dict[str, str], s2: dict[str, str]) -> None:
    reg = SchemaRegistry(mode=CompatibilityMode.NONE)
    reg.register("t", s1, now_ms=0)
    reg.register("t", s2, now_ms=1)
    assert reg.latest("t").version == 2


@given(st.lists(st.text(alphabet="ab", min_size=1, max_size=4), min_size=1, max_size=10))
@settings(max_examples=100)
def test_version_count_matches_registrations(subjects: list[str]) -> None:
    reg = SchemaRegistry(mode=CompatibilityMode.NONE)
    for sub in subjects:
        reg.register(sub, {"id": "int"}, now_ms=0)
    for sub in set(subjects):
        count = subjects.count(sub)
        assert len(reg.list_versions(sub)) == count
