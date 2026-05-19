"""Hypothesis properties — invariants of hash + sketch + heavy hitters."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cms.hash import hash64, index_for
from cms.heavy import exact_heavy_hitters, top_k_two_pass
from cms.schema import SketchConfig
from cms.sketch import estimate, merge, new_sketch, update

# ---------- hash properties --------------------------------------------------


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=30)
def test_property_hash64_deterministic(text: str) -> None:
    assert hash64(text, seed=0) == hash64(text, seed=0)


@given(
    text=st.text(min_size=0, max_size=50),
    width=st.integers(min_value=10, max_value=10_000),
    seed=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=30)
def test_property_index_in_range(text: str, width: int, seed: int) -> None:
    """index_for always returns a valid bucket."""
    idx = index_for(text, seed=seed, width=width)
    assert 0 <= idx < width


# ---------- CMS properties ---------------------------------------------------


@given(
    values=st.lists(
        st.text(min_size=1, max_size=8),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=20)
def test_property_estimate_at_least_true_count(values: list[str]) -> None:
    """For any inserted value, estimate >= true count (one-sided)."""
    s = new_sketch()
    true_counts: dict[str, int] = {}
    for v in values:
        s = update(s, v)
        true_counts[v] = true_counts.get(v, 0) + 1
    for v, c in true_counts.items():
        assert estimate(s, v) >= c


@given(
    values=st.lists(
        st.text(min_size=1, max_size=8),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=15)
def test_property_estimate_at_most_total_count(values: list[str]) -> None:
    """Estimate never exceeds total stream count."""
    s = new_sketch()
    for v in values:
        s = update(s, v)
    for v in set(values):
        assert estimate(s, v) <= s.total_count


@given(
    values=st.lists(
        st.text(min_size=1, max_size=8),
        min_size=1,
        max_size=30,
    ),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_property_merge_self_doubles(values: list[str]) -> None:
    """merge(s, s) gives counters that are exactly 2× the original."""
    s = new_sketch()
    for v in values:
        s = update(s, v)
    merged = merge(s, s)
    for i in range(s.depth):
        for j in range(s.width):
            assert merged.rows[i][j] == 2 * s.rows[i][j]


@given(
    values_a=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=20),
    values_b=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=20),
)
@settings(max_examples=15)
def test_property_merge_commutative(
    values_a: list[str],
    values_b: list[str],
) -> None:
    """merge(a, b).rows == merge(b, a).rows."""
    sa = new_sketch()
    sb = new_sketch()
    for v in values_a:
        sa = update(sa, v)
    for v in values_b:
        sb = update(sb, v)
    ab = merge(sa, sb)
    ba = merge(sb, sa)
    assert ab.rows == ba.rows


@given(
    values=st.lists(
        st.text(min_size=1, max_size=8),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=15)
def test_property_total_count_equals_inserts(values: list[str]) -> None:
    """sketch.total_count equals the number of update() calls."""
    s = new_sketch()
    for v in values:
        s = update(s, v)
    assert s.total_count == len(values)


@given(
    values=st.lists(
        st.text(min_size=1, max_size=5),
        min_size=20,
        max_size=200,
    ),
    k=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_cms_top_k_agrees_with_exact_on_dominant(
    values: list[str],
    k: int,
) -> None:
    """The top-1 element from CMS agrees with exact counting."""
    s = new_sketch(SketchConfig(epsilon=0.001, delta=0.001))
    for v in values:
        s = update(s, v)
    cms_hh = top_k_two_pass(s, values, k=k)
    exact_hh = exact_heavy_hitters(values, k=k)
    if exact_hh:
        # At least the #1 ranking should agree (large enough sketch).
        assert cms_hh[0].value == exact_hh[0].value
