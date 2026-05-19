"""Heavy-hitters extraction tests."""

from __future__ import annotations

import pytest

from cms.heavy import (
    HeavyHittersBuilder,
    exact_heavy_hitters,
    top_k_two_pass,
)
from cms.schema import SketchConfig
from cms.sketch import new_sketch, update


def _populate(values: list[str], config: SketchConfig | None = None) -> object:
    s = new_sketch(config)
    for v in values:
        s = update(s, v)
    return s


# ---------- top_k_two_pass ---------------------------------------------------


def test_top_k_two_pass_basic():
    values = ["A"] * 100 + ["B"] * 50 + ["C"] * 25 + ["D"] * 5
    sketch = _populate(values)
    hh = top_k_two_pass(sketch, values, k=3)
    assert [h.value for h in hh] == ["A", "B", "C"]
    assert hh[0].estimated_count >= 100
    assert abs(hh[0].fraction_of_total - 100 / 180) < 0.01


def test_top_k_two_pass_k_larger_than_distinct():
    values = ["A"] * 10 + ["B"] * 5
    sketch = _populate(values)
    hh = top_k_two_pass(sketch, values, k=10)
    # Only 2 distinct values
    assert len(hh) == 2


def test_top_k_two_pass_rejects_k_lt_1():
    sketch = _populate(["A"])
    with pytest.raises(ValueError, match="k must be >= 1"):
        top_k_two_pass(sketch, ["A"], k=0)


def test_top_k_two_pass_ranks_by_count_desc():
    """Estimates should be monotonically non-increasing in rank."""
    values = ["A"] * 100 + ["B"] * 80 + ["C"] * 60 + ["D"] * 40 + ["E"] * 20
    sketch = _populate(values)
    hh = top_k_two_pass(sketch, values, k=5)
    counts = [h.estimated_count for h in hh]
    assert counts == sorted(counts, reverse=True)


# ---------- HeavyHittersBuilder ---------------------------------------------


def test_builder_finds_dominant_value():
    """A clearly-dominant value always wins."""
    sketch = new_sketch()
    b = HeavyHittersBuilder(sketch=sketch, k=3, buffer=10)
    # 1000 of 'top' + 100 of various tail values
    for _ in range(1_000):
        b.add("top")
    for i in range(100):
        b.add(f"tail_{i}")
    hh = b.top_k()
    assert hh[0].value == "top"
    assert hh[0].estimated_count >= 1_000


def test_builder_drops_low_frequency_under_pressure():
    """When buffer is exceeded, low-freq candidates get evicted.

    Misra-Gries with ``k + buffer = 10`` slots is correct for values
    whose frequency > total / 10. We pick 5 heavies × 1000 = 5000
    (each well above 10% of total) plus 100 unique tail values, so
    heavies sit clearly above the eviction threshold.
    """
    sketch = new_sketch()
    b = HeavyHittersBuilder(sketch=sketch, k=5, buffer=5)
    for i in range(5):
        for _ in range(1_000):
            b.add(f"heavy_{i}")
    for i in range(100):
        b.add(f"tail_{i}")
    hh = b.top_k()
    # All top-K should be from the "heavy_" set.
    assert all(h.value.startswith("heavy_") for h in hh)


def test_builder_top_k_returns_at_most_k():
    sketch = new_sketch()
    b = HeavyHittersBuilder(sketch=sketch, k=3, buffer=5)
    for i in range(20):
        b.add(f"v_{i}")
    hh = b.top_k()
    assert len(hh) <= 3


# ---------- exact_heavy_hitters ---------------------------------------------


def test_exact_heavy_hitters():
    values = ["A"] * 100 + ["B"] * 50 + ["C"] * 25
    hh = exact_heavy_hitters(values, k=2)
    assert [h.value for h in hh] == ["A", "B"]
    assert hh[0].estimated_count == 100
    assert hh[0].fraction_of_total > 0.57


def test_exact_heavy_hitters_empty():
    assert exact_heavy_hitters([]) == []


def test_exact_heavy_hitters_rejects_k_zero():
    with pytest.raises(ValueError, match="k"):
        exact_heavy_hitters(["a"], k=0)


# ---------- CMS top-K agrees with exact top-K on dominant values -------------


def test_cms_top_k_agrees_with_exact_on_clear_winners():
    """When the top values dominate, CMS produces the same ranking."""
    values = ["w"] * 500 + ["x"] * 300 + ["y"] * 200 + [f"tail_{i}" for i in range(2_000)]
    sketch = _populate(values, SketchConfig(epsilon=0.001, delta=0.001))
    cms_hh = top_k_two_pass(sketch, values, k=3)
    exact_hh = exact_heavy_hitters(values, k=3)
    assert [h.value for h in cms_hh] == [h.value for h in exact_hh]
