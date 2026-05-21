"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from kllsketch.sketch import KLLSketch


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=500))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_n_equals_insertions(values: list[float]) -> None:
    s = KLLSketch(k=20)
    for v in values:
        s.update(v)
    assert s.n == len(values)


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=2, max_size=200))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_quantile_monotone(values: list[float]) -> None:
    s = KLLSketch(k=20)
    for v in values:
        s.update(v)
    q25 = s.quantile(0.25)
    q50 = s.quantile(0.5)
    q75 = s.quantile(0.75)
    assert q25 <= q50 <= q75


@given(
    st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=200),
    st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=200),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_merge_n_sum(a: list[float], b: list[float]) -> None:
    s1 = KLLSketch(k=20)
    for v in a:
        s1.update(v)
    s2 = KLLSketch(k=20)
    for v in b:
        s2.update(v)
    merged = s1.merge(s2)
    assert merged.n == len(a) + len(b)


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=500))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_cdf_between_0_and_1(values: list[float]) -> None:
    s = KLLSketch(k=20)
    for v in values:
        s.update(v)
    for probe in [values[0], values[-1]]:
        c = s.cdf(probe)
        assert 0.0 <= c <= 1.0
