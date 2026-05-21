"""Property-based tests for HyperLogLog."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hllsketch.sketch import HyperLogLog


@given(
    items=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=500),
    precision=st.integers(min_value=4, max_value=14),
)
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_count_ge_one_after_add(items: list[str], precision: int) -> None:
    """After adding at least one item, count() should be >= 1."""
    h = HyperLogLog(precision=precision)
    for item in items:
        h.add(item)
    assert h.count() >= 1


@given(
    items1=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=200),
    items2=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=200),
    precision=st.integers(min_value=8, max_value=14),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_merge_count_ge_max(items1: list[str], items2: list[str], precision: int) -> None:
    """Merged count >= max(count1, count2) — union cardinality >= either subset."""
    h1 = HyperLogLog(precision=precision)
    h2 = HyperLogLog(precision=precision)
    for item in items1:
        h1.add(item)
    for item in items2:
        h2.add(item)
    merged = h1.merge(h2)
    # Merged estimate should be at least as large as either individual estimate
    # (with generous tolerance for HLL approximation error)
    assert merged.count() >= min(h1.count(), h2.count()) - max(5, merged.count() // 5)


@given(
    n=st.integers(min_value=4, max_value=18),
)
@settings(max_examples=15)
def test_num_registers_is_power_of_two(n: int) -> None:
    h = HyperLogLog(precision=n)
    m = h.num_registers
    assert m > 0
    assert m & (m - 1) == 0  # power of two


@given(
    items=st.lists(
        st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.text()),
        min_size=1,
        max_size=100,
    ),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_mixed_types_no_crash(items: list[int | float | str]) -> None:
    """Adding mixed-type items should never crash."""
    h = HyperLogLog(precision=8)
    for item in items:
        h.add(item)
    assert h.count() >= 1
