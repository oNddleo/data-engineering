"""Levenshtein + nearest-neighbour."""

from __future__ import annotations

import pytest

from vnaddr.distance import find_closest, levenshtein

# ---------- levenshtein ------------------------------------------------------


def test_levenshtein_identical():
    assert levenshtein("hello", "hello") == 0


def test_levenshtein_empty_one_side():
    assert levenshtein("", "hello") == 5
    assert levenshtein("hello", "") == 5
    assert levenshtein("", "") == 0


def test_levenshtein_one_substitution():
    assert levenshtein("hello", "hallo") == 1


def test_levenshtein_one_insertion():
    assert levenshtein("hello", "helloo") == 1


def test_levenshtein_one_deletion():
    assert levenshtein("hello", "ello") == 1


def test_levenshtein_classic_kitten_sitting():
    assert levenshtein("kitten", "sitting") == 3


def test_levenshtein_symmetric():
    assert levenshtein("abc", "xyz") == levenshtein("xyz", "abc")


# ---------- find_closest -----------------------------------------------------


def test_find_closest_exact_in_haystack():
    out = find_closest("apple", ["apple", "banana", "cherry"])
    assert out == ("apple", 0)


def test_find_closest_typo():
    out = find_closest("appl", ["apple", "banana", "cherry"], max_distance=2)
    assert out == ("apple", 1)


def test_find_closest_none_within_distance():
    out = find_closest("zzz", ["apple", "banana"], max_distance=2)
    assert out is None


def test_find_closest_picks_min_distance():
    out = find_closest("orage", ["orange", "garage", "marble"], max_distance=2)
    # "orage" → "orange" (insert 'n', distance 1)
    assert out is not None
    assert out[0] == "orange"
    assert out[1] == 1


def test_find_closest_empty_haystack():
    out = find_closest("anything", [], max_distance=2)
    assert out is None


def test_find_closest_rejects_negative_distance():
    with pytest.raises(ValueError, match="max_distance"):
        find_closest("x", ["y"], max_distance=-1)


def test_find_closest_length_short_circuits():
    """Strings whose lengths differ by more than max_distance are skipped."""
    # "a" vs "abcdef" — length diff 5, max_distance 2 → skip.
    out = find_closest("a", ["abcdef"], max_distance=2)
    assert out is None
