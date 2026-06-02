"""Hypothesis properties — HLL invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hllpp.hash import hash64, leading_zeros_64
from hllpp.sketch import add, estimate, merge, new_sketch

# ---------- hash properties --------------------------------------------------


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=30)
def test_property_hash64_deterministic(text: str) -> None:
    """Same input → same hash."""
    assert hash64(text) == hash64(text)


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=30)
def test_property_hash64_in_uint64_range(text: str) -> None:
    """Hash is in [0, 2^64)."""
    h = hash64(text)
    assert 0 <= h < (1 << 64)


@given(
    x=st.integers(min_value=0, max_value=(1 << 60) - 1),
    width=st.integers(min_value=10, max_value=60),
)
@settings(max_examples=30)
def test_property_leading_zeros_bounded(x: int, width: int) -> None:
    """leading_zeros_64 is in [1, width+1]."""
    out = leading_zeros_64(x, max_zeros=width + 1)
    assert 1 <= out <= width + 1


# ---------- HLL properties ---------------------------------------------------


@given(
    n=st.integers(min_value=1, max_value=200),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=15)
def test_property_estimate_small_cardinality_near_exact(
    n: int,
    seed: int,
) -> None:
    """Small cardinalities (< 2.5m) use linear counting and are very accurate."""
    s = new_sketch(precision=14)
    for i in range(n):
        add(s, f"seed{seed}_v_{i}")
    e = estimate(s)
    # Linear counting at small n is near-exact (within ±2 typically)
    assert abs(e - n) <= max(5, n // 10)


@given(
    values=st.lists(
        st.text(min_size=1, max_size=10),
        min_size=1,
        max_size=50,
        unique=True,
    ),
)
@settings(max_examples=20)
def test_property_idempotent_inserts(values: list[str]) -> None:
    """Adding the same value twice doesn't change the sketch."""
    s = new_sketch(precision=10)
    for v in values:
        add(s, v)
    before = list(s.registers)
    for v in values:
        add(s, v)
    assert s.registers == before


@given(
    values=st.lists(
        st.text(min_size=1, max_size=10),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=20)
def test_property_merge_self_idempotent(values: list[str]) -> None:
    """merge(s, s) == s (element-wise max of equal arrays)."""
    s = new_sketch(precision=10)
    for v in values:
        add(s, v)
    merged = merge(s, s)
    assert merged.registers == s.registers


@given(
    a=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=30),
    b=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=30),
)
@settings(max_examples=15)
def test_property_merge_commutative(a: list[str], b: list[str]) -> None:
    """merge(a, b).registers == merge(b, a).registers."""
    sa = new_sketch(precision=10)
    sb = new_sketch(precision=10)
    for v in a:
        add(sa, v)
    for v in b:
        add(sb, v)
    ab = merge(sa, sb)
    ba = merge(sb, sa)
    assert ab.registers == ba.registers


@given(
    a=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=30),
    b=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=30),
)
@settings(max_examples=15)
def test_property_merge_dominates_single(a: list[str], b: list[str]) -> None:
    """Every register in merge(a, b) is ≥ the register in a (and in b)."""
    sa = new_sketch(precision=10)
    sb = new_sketch(precision=10)
    for v in a:
        add(sa, v)
    for v in b:
        add(sb, v)
    merged = merge(sa, sb)
    for i in range(merged.m):
        assert merged.registers[i] >= sa.registers[i]
        assert merged.registers[i] >= sb.registers[i]


@given(
    n=st.integers(min_value=100, max_value=5_000),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_duplicates_dont_change_estimate(
    n: int,
    seed: int,
) -> None:
    """Adding the same set of values twice yields the same estimate."""
    s = new_sketch(precision=12)
    values = [f"s{seed}_v_{i}" for i in range(n)]
    for v in values:
        add(s, v)
    e1 = estimate(s)
    for v in values:
        add(s, v)
    e2 = estimate(s)
    assert e1 == e2
