"""Hypothesis properties — invariants of detect + appliers."""

from __future__ import annotations

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from scdkit.appliers import apply_type_1, apply_type_2, type_2_current, type_2_empty
from scdkit.detect import detect
from scdkit.schema import VN_TZ, ChangeKind

_AS_OF = datetime(2026, 5, 17, 9, 0, tzinfo=VN_TZ)


@st.composite
def _snapshot(draw: st.DrawFn) -> dict[str, dict[str, str]]:
    keys = draw(
        st.lists(
            st.text(alphabet="ABCDEFGHIJ", min_size=1, max_size=3),
            min_size=0,
            max_size=8,
            unique=True,
        )
    )
    out: dict[str, dict[str, str]] = {}
    for k in keys:
        attrs_n = draw(st.integers(min_value=0, max_value=3))
        attrs: dict[str, str] = {}
        for i in range(attrs_n):
            attrs[f"a{i}"] = draw(st.sampled_from(["x", "y", "z"]))
        out[k] = attrs
    return out


@given(before=_snapshot(), after=_snapshot())
@settings(max_examples=100)
def test_detect_total_over_arbitrary_snapshots(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> None:
    """``detect`` returns a well-formed list for any input pair."""
    changes = detect(before, after, as_of=_AS_OF)
    for c in changes:
        if c.kind is ChangeKind.INSERT:
            assert c.before is None
            assert c.after is not None
        elif c.kind is ChangeKind.DELETE:
            assert c.before is not None
            assert c.after is None
        else:
            assert c.before is not None
            assert c.after is not None
            assert len(c.changed_attrs) > 0


@given(before=_snapshot(), after=_snapshot())
@settings(max_examples=100)
def test_detect_insert_keys_are_disjoint_set(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> None:
    """INSERT keys ⊆ after \\ before; DELETE keys ⊆ before \\ after."""
    changes = detect(before, after, as_of=_AS_OF)
    for c in changes:
        if c.kind is ChangeKind.INSERT:
            assert c.natural_key in after
            assert c.natural_key not in before
        elif c.kind is ChangeKind.DELETE:
            assert c.natural_key in before
            assert c.natural_key not in after


@given(before=_snapshot(), after=_snapshot())
@settings(max_examples=80)
def test_type_1_idempotent_on_no_op(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> None:
    """Applying ``detect(before, after)`` then ``detect(after, after)`` is a no-op."""
    changes_1 = detect(before, after, as_of=_AS_OF)
    state_1 = apply_type_1(
        {},
        [
            # Bootstrap: INSERTs for everything in `before` so the diff is meaningful.
            *(detect({}, before, as_of=_AS_OF)),
        ],
    )
    state_2 = apply_type_1(state_1, changes_1)
    state_3 = apply_type_1(state_2, detect(after, after, as_of=_AS_OF))
    assert state_2 == state_3


@given(before=_snapshot(), after=_snapshot())
@settings(max_examples=50)
def test_type_2_current_matches_after_snapshot(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> None:
    """After applying detect(before, after) Type-2 current view equals ``after`` (modulo metadata)."""
    bootstrap_changes = detect({}, before, as_of=_AS_OF)
    diff_changes = detect(before, after, as_of=_AS_OF)
    state = apply_type_2(type_2_empty(), bootstrap_changes)
    state = apply_type_2(state, diff_changes)
    current = type_2_current(state)
    # Keys present must match `after`.
    assert set(current.keys()) == set(after.keys())
    # And the attributes must match.
    for nk, attrs in after.items():
        assert current[nk].attributes == attrs


@given(before=_snapshot(), after=_snapshot())
@settings(max_examples=50)
def test_type_2_history_count_at_least_inserts_and_updates(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> None:
    """Type-2 history row count ≥ (#INSERTs + #UPDATEs) across both passes."""
    bootstrap_changes = detect({}, before, as_of=_AS_OF)
    diff_changes = detect(before, after, as_of=_AS_OF)
    state = apply_type_2(type_2_empty(), bootstrap_changes)
    state = apply_type_2(state, diff_changes)
    expected_at_least = sum(1 for c in bootstrap_changes if c.kind is ChangeKind.INSERT) + sum(
        1 for c in diff_changes if c.kind in (ChangeKind.INSERT, ChangeKind.UPDATE)
    )
    assert len(state.rows) >= expected_at_least


@given(before=_snapshot())
@settings(max_examples=50)
def test_self_diff_emits_no_changes(before: dict[str, dict[str, str]]) -> None:
    """``detect(s, s)`` is always empty."""
    assert detect(before, before, as_of=_AS_OF) == []
