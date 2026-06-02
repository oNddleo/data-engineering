"""Bloom filter core ops: build, add, contains, freeze, thaw, union, intersect."""

from __future__ import annotations

import pytest

from bloom.filter import (
    add,
    build,
    contains,
    freeze,
    intersect_estimate,
    thaw,
    union,
)


def test_build_basic() -> None:
    bf = build(capacity=1_000, target_fpr=0.01)
    assert bf.capacity == 1_000
    assert bf.target_fpr == 0.01
    assert bf.n_items == 0
    assert bf.size_bits >= 9_000  # 9.6 bits/item @ 1%


def test_no_false_negatives() -> None:
    """Every value added must contain() True. The Bloom guarantee."""
    bf = build(capacity=1_000, target_fpr=0.01)
    values = [f"v-{i}" for i in range(500)]
    for v in values:
        add(bf, v)
    for v in values:
        assert contains(bf, v) is True


def test_contains_empty_is_false() -> None:
    bf = build(capacity=100, target_fpr=0.01)
    assert contains(bf, "anything") is False


def test_low_false_positive_rate() -> None:
    """Empirical FPR on 10k random negatives should be near 1% target."""
    bf = build(capacity=10_000, target_fpr=0.01)
    # Fill to capacity.
    for i in range(10_000):
        add(bf, f"positive-{i}")
    # Probe with disjoint values.
    fp = sum(1 for i in range(10_000) if contains(bf, f"negative-{i}"))
    # Should be near 1% ± slack for stochastic variance.
    assert fp / 10_000 < 0.025


def test_freeze_round_trip() -> None:
    bf = build(capacity=100, target_fpr=0.01)
    for i in range(50):
        add(bf, f"v-{i}")
    snap = freeze(bf)
    assert snap.size_bits == bf.size_bits
    assert snap.n_hashes == bf.n_hashes
    assert snap.n_items == 50
    # Snapshot supports contains.
    for i in range(50):
        assert contains(snap, f"v-{i}") is True


def test_freeze_then_thaw() -> None:
    """thaw(freeze(bf)) preserves membership and structural fields."""
    bf = build(capacity=200, target_fpr=0.01)
    for i in range(100):
        add(bf, f"v-{i}")
    snap = freeze(bf)
    bf2 = thaw(snap, capacity=200, target_fpr=0.01)
    assert bf2.size_bits == bf.size_bits
    assert bf2.n_hashes == bf.n_hashes
    assert bf2.n_items == bf.n_items
    for i in range(100):
        assert contains(bf2, f"v-{i}") is True


def test_union_set_membership() -> None:
    """Union holds membership of both inputs (no false negatives)."""
    a = build(capacity=100, target_fpr=0.01)
    b = build(capacity=100, target_fpr=0.01)
    for v in ("alpha", "beta", "gamma"):
        add(a, v)
    for v in ("delta", "epsilon"):
        add(b, v)
    u = union(freeze(a), freeze(b))
    for v in ("alpha", "beta", "gamma", "delta", "epsilon"):
        assert contains(u, v) is True


def test_union_shape_mismatch_raises() -> None:
    a = freeze(build(100, target_fpr=0.01))
    b = freeze(build(200, target_fpr=0.01))
    with pytest.raises(ValueError, match="size_bits"):
        union(a, b)


def test_intersect_preserves_overlap() -> None:
    """Items in BOTH inputs must remain in the intersection."""
    a = build(capacity=100, target_fpr=0.01)
    b = build(capacity=100, target_fpr=0.01)
    for v in ("shared-1", "shared-2", "only-a"):
        add(a, v)
    for v in ("shared-1", "shared-2", "only-b"):
        add(b, v)
    i = intersect_estimate(freeze(a), freeze(b))
    assert contains(i, "shared-1") is True
    assert contains(i, "shared-2") is True


def test_intersect_shape_mismatch_raises() -> None:
    a = freeze(build(100, target_fpr=0.01))
    b = freeze(build(100, target_fpr=0.001))  # different size
    with pytest.raises(ValueError):
        intersect_estimate(a, b)


def test_contains_supports_non_string() -> None:
    bf = build(capacity=10, target_fpr=0.01)
    add(bf, 42)
    add(bf, 3.14)
    add(bf, b"bytes")
    assert contains(bf, 42) is True
    assert contains(bf, 3.14) is True
    assert contains(bf, b"bytes") is True


def test_build_validates_inputs() -> None:
    with pytest.raises(ValueError):
        build(capacity=0, target_fpr=0.01)
    with pytest.raises(ValueError):
        build(capacity=100, target_fpr=0.0)
