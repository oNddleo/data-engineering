"""Behaviour of all five SCD-type appliers."""

from __future__ import annotations

from datetime import timedelta

from scdkit.appliers import (
    apply_type_1,
    apply_type_2,
    apply_type_3,
    apply_type_4,
    apply_type_6,
    type_2_current,
    type_2_empty,
    type_2_history_for,
    type_4_empty,
    type_6_empty,
)
from scdkit.schema import HIGH_DATE, DimensionChange

from ._fixtures import DEFAULT_TS, make_change, make_delete_change, make_update_change

# ---------- TYPE 1 -----------------------------------------------------------


def test_type_1_insert_creates_row():
    result = apply_type_1({}, [make_change()])
    assert "S-001" in result
    assert result["S-001"].attributes["shop_name"] == "Shop Saigon"


def test_type_1_update_overwrites_in_place():
    initial = apply_type_1({}, [make_change()])
    result = apply_type_1(initial, [make_update_change(after={"shop_name": "New", "tier": "MALL"})])
    assert result["S-001"].attributes["shop_name"] == "New"
    assert result["S-001"].attributes["tier"] == "MALL"
    # No history kept — same single row.
    assert len(result) == 1


def test_type_1_delete_removes_row():
    initial = apply_type_1({}, [make_change()])
    result = apply_type_1(initial, [make_delete_change()])
    assert "S-001" not in result


def test_type_1_doesnt_mutate_input():
    initial = apply_type_1({}, [make_change()])
    snapshot = dict(initial)
    apply_type_1(initial, [make_update_change(after={"shop_name": "Touched", "tier": "BASIC"})])
    # Input dict unchanged.
    assert snapshot == initial


# ---------- TYPE 2 -----------------------------------------------------------


def test_type_2_insert_opens_row():
    state = apply_type_2(type_2_empty(), [make_change()])
    [row] = state.rows.values()
    assert row.surrogate_key == 1
    assert row.is_current is True
    assert row.effective_to == HIGH_DATE


def test_type_2_update_closes_prior_and_opens_new():
    state = apply_type_2(type_2_empty(), [make_change()])
    later = DEFAULT_TS + timedelta(days=1)
    state = apply_type_2(
        state,
        [make_update_change(detected_at=later, after={"shop_name": "New", "tier": "STANDARD"})],
    )
    history = type_2_history_for(state, "S-001")
    assert len(history) == 2
    # Earlier row closed.
    assert history[0].effective_to == later
    assert history[0].is_current is False
    # New row open.
    assert history[1].is_current is True
    assert history[1].effective_from == later


def test_type_2_surrogate_keys_monotonically_increasing():
    changes: list[DimensionChange] = [
        make_change(natural_key="S-1", after={"x": "v"}),
        make_change(natural_key="S-2", after={"x": "w"}),
        make_change(natural_key="S-3", after={"x": "y"}),
    ]
    state = apply_type_2(type_2_empty(), changes)
    sks = sorted(state.rows.keys())
    assert sks == [1, 2, 3]


def test_type_2_chained_batches_share_surrogate_counter():
    state = apply_type_2(type_2_empty(start_surrogate=100), [make_change()])
    assert next(iter(state.rows)) == 100
    state = apply_type_2(state, [make_change(natural_key="S-002", after={"x": "y"})])
    assert sorted(state.rows.keys()) == [100, 101]


def test_type_2_delete_closes_without_inserting_tombstone():
    state = apply_type_2(type_2_empty(), [make_change()])
    later = DEFAULT_TS + timedelta(days=2)
    state = apply_type_2(state, [make_delete_change(detected_at=later)])
    # Row still exists in history, but is_current is False.
    [row] = state.rows.values()
    assert row.is_current is False
    assert row.effective_to == later
    # Not in current-by-natural anymore.
    assert "S-001" not in state.current_by_natural


def test_type_2_current_view():
    state = apply_type_2(
        type_2_empty(),
        [
            make_change(natural_key="S-1", after={"x": "1"}),
            make_change(natural_key="S-2", after={"x": "2"}),
        ],
    )
    current = type_2_current(state)
    assert set(current.keys()) == {"S-1", "S-2"}


def test_type_2_history_for_unknown_returns_empty():
    state = apply_type_2(type_2_empty(), [make_change()])
    assert type_2_history_for(state, "NOT-PRESENT") == []


# ---------- TYPE 3 -----------------------------------------------------------


def test_type_3_update_stashes_previous():
    initial = apply_type_3({}, [make_change()], tracked_attrs=["shop_name"])
    later = make_update_change(
        before={"shop_name": "Shop Saigon", "tier": "STANDARD"},
        after={"shop_name": "Renamed", "tier": "STANDARD"},
    )
    result = apply_type_3(initial, [later], tracked_attrs=["shop_name"])
    assert result["S-001"].attributes["shop_name"] == "Renamed"
    assert result["S-001"].previous_attributes["shop_name"] == "Shop Saigon"


def test_type_3_keeps_only_one_prior_version():
    """A second update overwrites previous_attributes — Type 3 doesn't chain."""
    initial = apply_type_3({}, [make_change()], tracked_attrs=["shop_name"])
    upd1 = make_update_change(
        before={"shop_name": "Shop Saigon", "tier": "STANDARD"},
        after={"shop_name": "Mid", "tier": "STANDARD"},
    )
    upd2 = make_update_change(
        before={"shop_name": "Mid", "tier": "STANDARD"},
        after={"shop_name": "Latest", "tier": "STANDARD"},
    )
    after_first = apply_type_3(initial, [upd1], tracked_attrs=["shop_name"])
    after_second = apply_type_3(after_first, [upd2], tracked_attrs=["shop_name"])
    assert after_second["S-001"].previous_attributes["shop_name"] == "Mid"


def test_type_3_delete_removes_row():
    initial = apply_type_3({}, [make_change()], tracked_attrs=["shop_name"])
    result = apply_type_3(initial, [make_delete_change()], tracked_attrs=["shop_name"])
    assert "S-001" not in result


# ---------- TYPE 4 -----------------------------------------------------------


def test_type_4_insert_to_current_table():
    state = apply_type_4(type_4_empty(), [make_change()])
    assert "S-001" in state.current
    assert state.history == []


def test_type_4_update_archives_prior():
    state = apply_type_4(type_4_empty(), [make_change()])
    later = DEFAULT_TS + timedelta(days=1)
    state = apply_type_4(
        state,
        [make_update_change(detected_at=later, after={"shop_name": "New", "tier": "STANDARD"})],
    )
    assert state.current["S-001"].attributes["shop_name"] == "New"
    assert len(state.history) == 1
    assert state.history[0].effective_to == later
    assert state.history[0].is_current is False


def test_type_4_delete_archives_and_removes():
    state = apply_type_4(type_4_empty(), [make_change()])
    later = DEFAULT_TS + timedelta(days=1)
    state = apply_type_4(state, [make_delete_change(detected_at=later)])
    assert "S-001" not in state.current
    assert len(state.history) == 1


# ---------- TYPE 6 -----------------------------------------------------------


def test_type_6_insert_creates_current_and_history():
    state = apply_type_6(type_6_empty(), [make_change()], tracked_attrs=["shop_name"])
    assert "S-001" in state.current
    assert len(state.history) == 1


def test_type_6_update_maintains_all_three_views():
    state = apply_type_6(type_6_empty(), [make_change()], tracked_attrs=["shop_name"])
    later = DEFAULT_TS + timedelta(days=1)
    # The UPDATE's ``before`` must match what's in state for the previous-attr test
    # to be meaningful — the applier reads ``previous_attributes`` from ``ch.before``.
    state = apply_type_6(
        state,
        [
            make_update_change(
                detected_at=later,
                before={"shop_name": "Shop Saigon", "tier": "STANDARD"},
                after={"shop_name": "New", "tier": "STANDARD"},
            )
        ],
        tracked_attrs=["shop_name"],
    )
    # Type 1: latest attrs.
    assert state.current["S-001"].attributes["shop_name"] == "New"
    # Type 3: previous value comes from the change's ``before``.
    assert state.current["S-001"].previous_attributes["shop_name"] == "Shop Saigon"
    # Type 2: two history rows.
    assert len(state.history) == 2
    versions = sorted(state.history.values(), key=lambda r: r.surrogate_key or 0)
    assert versions[0].is_current is False
    assert versions[1].is_current is True


def test_type_6_delete_closes_history_and_drops_current():
    state = apply_type_6(type_6_empty(), [make_change()], tracked_attrs=["shop_name"])
    later = DEFAULT_TS + timedelta(days=1)
    state = apply_type_6(
        state, [make_delete_change(detected_at=later)], tracked_attrs=["shop_name"]
    )
    assert "S-001" not in state.current
    [row] = state.history.values()
    assert row.is_current is False
