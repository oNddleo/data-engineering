"""Schema invariants: Reservoir, BuildableReservoir, WeightedReservoir."""

from __future__ import annotations

import pytest

from reservoir.schema import (
    BuildableReservoir,
    Reservoir,
    WeightedItem,
    WeightedReservoir,
)

# ---------- Reservoir -------------------------------------------------------


def test_reservoir_basic() -> None:
    r = Reservoir(capacity=10, items=("a", "b", "c"), n_seen=100)
    assert r.n_kept == 3
    assert r.fill_ratio == 0.3


def test_reservoir_empty_fill_ratio_zero() -> None:
    r = Reservoir(capacity=10, items=(), n_seen=0)
    assert r.fill_ratio == 0.0


def test_reservoir_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        Reservoir(capacity=0, items=(), n_seen=0)


def test_reservoir_rejects_negative_n_seen() -> None:
    with pytest.raises(ValueError, match="n_seen"):
        Reservoir(capacity=10, items=(), n_seen=-1)


def test_reservoir_rejects_overfull() -> None:
    with pytest.raises(ValueError, match="overfull"):
        Reservoir(capacity=2, items=("a", "b", "c"), n_seen=5)


# ---------- BuildableReservoir ---------------------------------------------


def test_buildable_basic() -> None:
    res = BuildableReservoir(capacity=10)
    assert res.capacity == 10
    assert res.n_seen == 0
    assert res.items == []


def test_buildable_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        BuildableReservoir(capacity=0)


def test_buildable_rejects_negative_w() -> None:
    with pytest.raises(ValueError, match="_w"):
        BuildableReservoir(capacity=10, _w=-1.0)


def test_buildable_rejects_overfull() -> None:
    with pytest.raises(ValueError, match="overfull"):
        BuildableReservoir(capacity=2, items=["a", "b", "c"])


# ---------- WeightedItem ---------------------------------------------------


def test_weighted_item_basic() -> None:
    w = WeightedItem(value="x", weight=2.0, key=0.5)
    assert w.value == "x"


def test_weighted_item_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="weight"):
        WeightedItem(value="x", weight=-0.1, key=0.5)


def test_weighted_item_rejects_zero_weight() -> None:
    with pytest.raises(ValueError, match="weight"):
        WeightedItem(value="x", weight=0.0, key=0.5)


def test_weighted_item_rejects_out_of_range_key() -> None:
    with pytest.raises(ValueError, match="key"):
        WeightedItem(value="x", weight=1.0, key=1.5)
    with pytest.raises(ValueError, match="key"):
        WeightedItem(value="x", weight=1.0, key=-0.1)


# ---------- WeightedReservoir ----------------------------------------------


def test_weighted_reservoir_basic() -> None:
    wr = WeightedReservoir(capacity=10)
    assert wr.capacity == 10
    assert wr.total_weight_seen == 0.0


def test_weighted_reservoir_rejects_unsorted() -> None:
    items = [
        WeightedItem("a", 1.0, 0.9),
        WeightedItem("b", 1.0, 0.5),  # smaller key after larger
    ]
    with pytest.raises(ValueError, match="not sorted"):
        WeightedReservoir(capacity=10, items=items)


def test_weighted_reservoir_rejects_overfull() -> None:
    items = [
        WeightedItem("a", 1.0, 0.1),
        WeightedItem("b", 1.0, 0.2),
        WeightedItem("c", 1.0, 0.3),
    ]
    with pytest.raises(ValueError, match="overfull"):
        WeightedReservoir(capacity=2, items=items)


def test_weighted_reservoir_rejects_negative_total_weight() -> None:
    with pytest.raises(ValueError, match="total_weight_seen"):
        WeightedReservoir(capacity=10, total_weight_seen=-1.0)
