"""CMS core — update / estimate / merge."""

from __future__ import annotations

import pytest

from cms.schema import SketchConfig
from cms.sketch import estimate, merge, new_sketch, stats, update


def _build(values: list[str], config: SketchConfig | None = None) -> object:
    s = new_sketch(config)
    for v in values:
        s = update(s, v)
    return s


# ---------- update + estimate -----------------------------------------------


def test_empty_sketch_estimates_zero():
    s = new_sketch()
    assert estimate(s, "anything") == 0


def test_single_insert_estimates_one():
    s = new_sketch()
    s = update(s, "hello")
    assert estimate(s, "hello") >= 1
    # over-estimation never produces > 1 for the only insert
    assert estimate(s, "hello") == 1


def test_unseen_value_can_have_nonzero_estimate():
    """A small sketch may collide unseen values; estimate is non-negative."""
    s = new_sketch(SketchConfig(epsilon=0.5, delta=0.5))  # tiny: w=6, d=1
    for i in range(100):
        s = update(s, f"v_{i}")
    # Unseen value: estimate is non-negative (over-counts at worst).
    e = estimate(s, "never-inserted")
    assert e >= 0


def test_estimate_is_overestimate_only():
    """Estimate ≥ true count for any inserted value."""
    s = new_sketch()
    inserts = ["a"] * 50 + ["b"] * 30 + ["c"] * 20
    for v in inserts:
        s = update(s, v)
    assert estimate(s, "a") >= 50
    assert estimate(s, "b") >= 30
    assert estimate(s, "c") >= 20


def test_estimate_within_error_bound():
    """For a Zipf-skewed stream, estimate error ≤ ε · total_count."""
    s = new_sketch(SketchConfig(epsilon=0.01, delta=0.01))
    # Build a stream where a few values dominate.
    values = ["heavy"] * 1_000 + [f"v_{i}" for i in range(2_000)]
    for v in values:
        s = update(s, v)
    bound = int(0.01 * s.total_count)
    # The "heavy" value's estimate should be very close to 1000.
    e = estimate(s, "heavy")
    assert 1_000 <= e <= 1_000 + bound


def test_update_count_n():
    """update(s, v, count=N) is equivalent to N single updates."""
    s1 = new_sketch()
    s1 = update(s1, "x", count=10)
    s2 = new_sketch()
    for _ in range(10):
        s2 = update(s2, "x")
    assert s1.rows == s2.rows
    assert s1.total_count == s2.total_count


def test_update_rejects_negative_count():
    s = new_sketch()
    with pytest.raises(ValueError, match="count"):
        update(s, "x", count=-1)


def test_update_zero_count_is_noop():
    s = new_sketch()
    out = update(s, "x", count=0)
    assert out.total_count == 0
    assert estimate(out, "x") == 0


# ---------- merge ------------------------------------------------------------


def test_merge_disjoint_streams_sums():
    """Merging two same-config sketches sums their counters."""
    s_a = _build(["x"] * 5 + ["y"] * 3)
    s_b = _build(["z"] * 7)
    merged = merge(s_a, s_b)
    assert merged.total_count == s_a.total_count + s_b.total_count
    # x and y appear only in s_a; merged estimate matches s_a's.
    assert estimate(merged, "x") >= 5
    assert estimate(merged, "z") >= 7


def test_merge_overlapping_streams_doubles():
    """Merging two sketches over the same input doubles all counts."""
    s_a = _build(["x"] * 100)
    s_b = _build(["x"] * 100)
    merged = merge(s_a, s_b)
    assert estimate(merged, "x") >= 200


def test_merge_rejects_different_configs():
    s_a = new_sketch(SketchConfig(epsilon=0.01, delta=0.01))
    s_b = new_sketch(SketchConfig(epsilon=0.001, delta=0.001))
    with pytest.raises(ValueError, match="same config"):
        merge(s_a, s_b)


def test_merge_empty_returns_empty():
    merged = merge()
    assert merged.total_count == 0


def test_merge_single_sketch_is_identity():
    s = _build(["x"] * 5)
    merged = merge(s)
    assert estimate(merged, "x") == estimate(s, "x")


# ---------- stats ------------------------------------------------------------


def test_stats_for_empty_sketch():
    summary = stats(new_sketch())
    assert summary.total_count == 0
    assert summary.max_counter == 0
    assert summary.standard_error_bound == 0


def test_stats_for_filled_sketch():
    s = _build(["x"] * 1_000)
    summary = stats(s)
    assert summary.total_count == 1_000
    assert summary.max_counter >= 1_000
    assert summary.standard_error_bound > 0
