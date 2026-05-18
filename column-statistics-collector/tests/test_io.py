"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from colstats.io_jsonl import (
    dump_profiles,
    load_profiles,
    profile_from_dict,
    profile_to_dict,
)
from colstats.profile import collect_profile
from colstats.schema import ColumnKind


def test_profile_round_trip_numeric():
    p = collect_profile("x", [str(v) for v in range(1, 101)], kind=ColumnKind.NUMERIC)
    assert profile_from_dict(profile_to_dict(p)) == p


def test_profile_round_trip_categorical():
    p = collect_profile("cat", ["A"] * 5 + ["B"] * 3, kind=ColumnKind.CATEGORICAL)
    assert profile_from_dict(profile_to_dict(p)) == p


def test_profile_round_trip_string():
    p = collect_profile("name", ["alice", "bob", "carol"], kind=ColumnKind.STRING)
    assert profile_from_dict(profile_to_dict(p)) == p


def test_profile_round_trip_date():
    p = collect_profile("dob", ["2026-01-01", "2026-06-15"], kind=ColumnKind.DATE)
    assert profile_from_dict(profile_to_dict(p)) == p


def test_dump_load_round_trip():
    p1 = collect_profile("a", [str(v) for v in range(10)], kind=ColumnKind.NUMERIC)
    p2 = collect_profile("b", ["A"] * 5, kind=ColumnKind.CATEGORICAL)
    assert load_profiles(dump_profiles([p1, p2])) == [p1, p2]


def test_dump_emits_newline_terminated():
    p = collect_profile("a", ["x"], kind=ColumnKind.STRING)
    text = dump_profiles([p])
    assert text.endswith("\n")


def test_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_profiles("[1, 2]\n")


def test_load_rejects_bool_n_rows():
    """A bool sneaking in as int must be rejected."""
    p = collect_profile("x", ["1", "2"], kind=ColumnKind.NUMERIC)
    bad = profile_to_dict(p)
    bad["n_rows"] = True
    with pytest.raises(TypeError, match="n_rows must be int"):
        profile_from_dict(bad)


def test_load_rejects_non_list_top_k():
    p = collect_profile("x", ["A"], kind=ColumnKind.CATEGORICAL)
    bad = profile_to_dict(p)
    bad["top_k"] = "not a list"
    with pytest.raises(TypeError, match="top_k must be list"):
        profile_from_dict(bad)
