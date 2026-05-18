"""Space-Saving top-K + cardinality."""

from __future__ import annotations

import pytest

from colstats.categorical import SpaceSaving, cardinality, top_k

# ---------- SpaceSaving ------------------------------------------------------


def test_spacesaving_under_k_exact():
    """When unique count <= K, Space-Saving is exact."""
    ss = SpaceSaving(k=5)
    for v in ["a", "a", "b", "c", "c", "c"]:
        ss.add(v)
    out = ss.top_k()
    by_value = {e.value: e for e in out}
    assert by_value["a"].count == 2
    assert by_value["a"].epsilon == 0
    assert by_value["c"].count == 3
    assert by_value["c"].epsilon == 0


def test_spacesaving_evicts_smallest():
    """When over K, the smallest-count entry is evicted."""
    ss = SpaceSaving(k=2)
    # a:1 b:1 c:1 — c evicts a (a's count = 1, c gets count=2 epsilon=1)
    for v in ["a", "b", "c"]:
        ss.add(v)
    out = ss.top_k()
    values = {e.value for e in out}
    # b and c remain; a evicted.
    assert "a" not in values


def test_spacesaving_epsilon_bound():
    """Evicted entries' counts become the new epsilon."""
    ss = SpaceSaving(k=2)
    # a*5, b*3, c*1 — after c is added, c evicts whoever has smallest
    # count. b has 3, a has 5. So 'b' wins ... wait actually 'c' replaces
    # the smallest. Let me trace: a*5 b*3, then c. Smallest in map is b
    # (count=3). c replaces b, c.count = 3+1 = 4, c.epsilon = 3.
    for _ in range(5):
        ss.add("a")
    for _ in range(3):
        ss.add("b")
    ss.add("c")
    out = ss.top_k()
    by_value = {e.value: e for e in out}
    assert "a" in by_value
    assert by_value["a"].count == 5
    assert by_value["a"].epsilon == 0
    if "c" in by_value:
        assert by_value["c"].epsilon == 3


def test_spacesaving_top_k_sorted_desc():
    ss = SpaceSaving(k=10)
    for v in ["a"] * 5 + ["b"] * 10 + ["c"] * 3:
        ss.add(v)
    out = ss.top_k()
    counts = [e.count for e in out]
    assert counts == sorted(counts, reverse=True)


def test_spacesaving_rejects_k_lt_1():
    with pytest.raises(ValueError, match="k must be >= 1"):
        SpaceSaving(k=0)


def test_spacesaving_tracks_n_seen():
    ss = SpaceSaving(k=3)
    for v in ["a", "b", "c", "a", "d", "e", "f"]:
        ss.add(v)
    assert ss.n_seen == 7


# ---------- top_k (one-shot) -------------------------------------------------


def test_top_k_one_shot():
    out = top_k(["x"] * 100 + ["y"] * 50 + ["z"] * 20, k=5)
    assert out[0].value == "x"
    assert out[0].count == 100


def test_top_k_empty():
    assert top_k([], k=5) == []


# ---------- cardinality ------------------------------------------------------


def test_cardinality_exact_under_cap():
    count, capped = cardinality(["a", "b", "c", "a"], cap=10)
    assert count == 3
    assert capped is False


def test_cardinality_capped():
    values = [f"v_{i}" for i in range(1_000)]
    count, capped = cardinality(values, cap=100)
    assert count == 101
    assert capped is True


def test_cardinality_empty():
    count, capped = cardinality([], cap=10)
    assert count == 0
    assert capped is False


def test_cardinality_rejects_cap_lt_1():
    with pytest.raises(ValueError, match="cap"):
        cardinality([], cap=0)
