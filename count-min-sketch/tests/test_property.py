"""Property-based tests for Count-Min Sketch."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cmsketch.sketch import CountMinSketch


@given(
    items=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=200),
    width=st.integers(min_value=10, max_value=256),
    depth=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
def test_estimate_always_ge_true_count(items: list[str], width: int, depth: int) -> None:
    """Fundamental CMS guarantee: estimate >= true count for all items."""
    s = CountMinSketch(width=width, depth=depth)
    true: dict[str, int] = {}
    for item in items:
        s.update(item)
        true[item] = true.get(item, 0) + 1
    for item, cnt in true.items():
        assert s.query(item) >= cnt


@given(
    counts=st.lists(st.integers(min_value=1, max_value=50), min_size=1, max_size=50),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_n_tracks_total_updates(counts: list[int]) -> None:
    """n equals sum of all count arguments passed to update."""
    s = CountMinSketch(width=64, depth=3)
    total = 0
    for i, cnt in enumerate(counts):
        s.update(f"item_{i}", count=cnt)
        total += cnt
    assert s.n == total


@given(
    items1=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=100),
    items2=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=100),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_merge_n_equals_sum(items1: list[str], items2: list[str]) -> None:
    """Merged sketch n == n1 + n2."""
    s1 = CountMinSketch(width=128, depth=4, seed=0)
    s2 = CountMinSketch(width=128, depth=4, seed=0)
    for item in items1:
        s1.update(item)
    for item in items2:
        s2.update(item)
    merged = s1.merge(s2)
    assert merged.n == s1.n + s2.n


@given(
    items1=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=100),
    items2=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=100),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_merge_estimate_ge_true_union_count(items1: list[str], items2: list[str]) -> None:
    """Merged sketch estimate >= true count from both streams combined."""
    s1 = CountMinSketch(width=256, depth=4, seed=0)
    s2 = CountMinSketch(width=256, depth=4, seed=0)
    true: dict[str, int] = {}
    for item in items1:
        s1.update(item)
        true[item] = true.get(item, 0) + 1
    for item in items2:
        s2.update(item)
        true[item] = true.get(item, 0) + 1
    merged = s1.merge(s2)
    for item, cnt in true.items():
        assert merged.query(item) >= cnt


@given(st.integers(min_value=2, max_value=1000), st.integers(min_value=1, max_value=10))
@settings(max_examples=30)
def test_size_equals_width_times_depth(width: int, depth: int) -> None:
    s = CountMinSketch(width=width, depth=depth)
    assert s.size() == width * depth
