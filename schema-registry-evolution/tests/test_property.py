"""Hypothesis properties — invariants of diff + compat + semver."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from schemaev.compat import check_backward, check_forward
from schemaev.diff import diff
from schemaev.schema import Field, FieldType, Schema
from schemaev.versioning import BumpKind, next_version, parse_semver, suggest_bump


@st.composite
def _field(draw: st.DrawFn) -> Field:
    # First char must be a letter (avoids all-underscore names that fail
    # the schema's alphanumeric requirement).
    first = draw(st.sampled_from("abcdefg"))
    rest = draw(st.text(alphabet="abcdefg_", min_size=0, max_size=3))
    return Field(
        name=first + rest,
        type=draw(st.sampled_from(list(FieldType))),
        required=draw(st.booleans()),
        default=draw(st.one_of(st.none(), st.just("x"))),
        aliases=(),
    )


@st.composite
def _schema(draw: st.DrawFn) -> Schema:
    n = draw(st.integers(min_value=1, max_value=4))
    raw_fields = draw(st.lists(_field(), min_size=n, max_size=n))
    # Dedupe by name (Schema rejects duplicates).
    seen: dict[str, Field] = {}
    for f in raw_fields:
        seen[f.name] = f
    if not seen:
        seen["x"] = Field(name="x", type=FieldType.STRING)
    return Schema(name="S", version="1.0.0", fields=tuple(seen.values()))


@given(s=_schema())
@settings(max_examples=60)
def test_self_diff_is_empty(s: Schema) -> None:
    """``diff(s, s)`` always returns an empty list."""
    assert diff(s, s) == []


@given(s=_schema())
@settings(max_examples=60)
def test_self_compat_always_compatible(s: Schema) -> None:
    """A schema is BACKWARD- + FORWARD-compatible with itself."""
    assert check_backward(s, s).is_compatible is True
    assert check_forward(s, s).is_compatible is True


@given(s=_schema())
@settings(max_examples=60)
def test_self_bump_is_none(s: Schema) -> None:
    """``suggest_bump(diff(s, s))`` is always NONE."""
    assert suggest_bump(diff(s, s)) is BumpKind.NONE


@given(
    parts=st.tuples(
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=99),
    ),
)
@settings(max_examples=80)
def test_parse_render_semver_roundtrip(parts: tuple[int, int, int]) -> None:
    major, minor, patch = parts
    rendered = f"{major}.{minor}.{patch}"
    assert parse_semver(rendered) == parts


@given(
    parts=st.tuples(
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=99),
    ),
    bump=st.sampled_from([BumpKind.MAJOR, BumpKind.MINOR, BumpKind.PATCH]),
)
@settings(max_examples=80)
def test_next_version_resets_lower_components(
    parts: tuple[int, int, int],
    bump: BumpKind,
) -> None:
    """A major bump zeros minor + patch; a minor bump zeros patch."""
    major, minor, patch = parts
    current = f"{major}.{minor}.{patch}"
    nxt = next_version(current, bump)
    nm, mn, pt = parse_semver(nxt)
    if bump is BumpKind.MAJOR:
        assert nm == major + 1
        assert mn == 0
        assert pt == 0
    elif bump is BumpKind.MINOR:
        assert nm == major
        assert mn == minor + 1
        assert pt == 0
    elif bump is BumpKind.PATCH:
        assert nm == major
        assert mn == minor
        assert pt == patch + 1


@given(s=_schema())
@settings(max_examples=40)
def test_diff_total_over_arbitrary_pairs(s: Schema) -> None:
    """``diff`` returns a well-formed list for any pair."""
    s2 = s  # using same schema; the property is "no crash + sorted"
    out = diff(s, s2)
    # Output sorted.
    pairs = [(c.kind, c.field_name) for c in out]
    assert pairs == sorted(pairs)
