"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from scdkit.schema import HIGH_DATE, VN_TZ, ChangeKind, DimensionChange, SCDType

from ._fixtures import DEFAULT_TS, make_change, make_row


def test_vn_tz_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_high_date_is_far_future():
    assert HIGH_DATE.year == 9999


def test_scd_type_enum_five_values():
    assert {t.value for t in SCDType} == {
        "TYPE_1",
        "TYPE_2",
        "TYPE_3",
        "TYPE_4",
        "TYPE_6",
    }


def test_change_kind_three_values():
    assert {k.value for k in ChangeKind} == {"INSERT", "UPDATE", "DELETE"}


def test_row_rejects_empty_natural_key():
    with pytest.raises(ValueError):
        make_row(natural_key="")


def test_row_rejects_naive_effective_from():
    with pytest.raises(ValueError):
        make_row(effective_from=datetime(2026, 5, 17))


def test_row_rejects_effective_from_after_to():
    with pytest.raises(ValueError, match="effective_from"):
        make_row(
            effective_from=DEFAULT_TS,
            effective_to=datetime(2026, 1, 1, tzinfo=VN_TZ),
        )


def test_row_accepts_equal_from_and_to():
    """Open-and-close at same instant — degenerate but legal."""
    r = make_row(effective_from=DEFAULT_TS, effective_to=DEFAULT_TS)
    assert r.effective_from == r.effective_to


def test_change_insert_rejects_non_null_before():
    with pytest.raises(ValueError, match="INSERT"):
        DimensionChange(
            natural_key="S",
            kind=ChangeKind.INSERT,
            detected_at=DEFAULT_TS,
            before={"x": "y"},
            after={"x": "y"},
        )


def test_change_delete_rejects_non_null_after():
    with pytest.raises(ValueError, match="DELETE"):
        DimensionChange(
            natural_key="S",
            kind=ChangeKind.DELETE,
            detected_at=DEFAULT_TS,
            before={"x": "y"},
            after={"x": "y"},
        )


def test_change_update_requires_both_sides():
    with pytest.raises(ValueError, match="UPDATE"):
        DimensionChange(
            natural_key="S",
            kind=ChangeKind.UPDATE,
            detected_at=DEFAULT_TS,
            before=None,
            after={"x": "y"},
            changed_attrs=("x",),
        )


def test_change_update_requires_changed_attrs():
    with pytest.raises(ValueError, match="UPDATE"):
        DimensionChange(
            natural_key="S",
            kind=ChangeKind.UPDATE,
            detected_at=DEFAULT_TS,
            before={"x": "1"},
            after={"x": "2"},
            changed_attrs=(),
        )


def test_change_rejects_naive_detected_at():
    with pytest.raises(ValueError):
        DimensionChange(
            natural_key="S",
            kind=ChangeKind.INSERT,
            detected_at=datetime(2026, 5, 17),
            before=None,
            after={"x": "y"},
        )


def test_default_change_legal():
    """Fixture builds a legal default INSERT change."""
    c = make_change()
    assert c.kind is ChangeKind.INSERT
    assert c.before is None
