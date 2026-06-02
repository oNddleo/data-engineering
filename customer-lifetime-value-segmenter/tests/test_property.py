"""Hypothesis properties — invariants of the RFM + segment + CLV pipeline."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from clvseg.clv import forecast
from clvseg.schema import Segment
from clvseg.segments import classify_all, rfm_to_segment

from ._fixtures import make_score


@given(
    r=st.integers(min_value=1, max_value=5),
    f=st.integers(min_value=1, max_value=5),
    m=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=125)  # 5^3 = 125 — exhaustively cover the RFM cube
def test_rfm_to_segment_total(r: int, f: int, m: int) -> None:
    """Every legal (R, F, M) triple maps to exactly one segment — never raises."""
    seg = rfm_to_segment(r, f, m)
    assert isinstance(seg, Segment)


@given(
    f=st.integers(min_value=1, max_value=5),
    m=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_r_score_5_with_high_f_is_top_segment(f: int, m: int) -> None:
    """R=5 + F=5 is always CHAMPIONS, regardless of M."""
    if f == 5:
        assert rfm_to_segment(5, 5, m) is Segment.CHAMPIONS


@given(
    f=st.integers(min_value=1, max_value=5),
    m=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_r_score_1_low_f_is_bottom_segment(f: int, m: int) -> None:
    """R=1 + F=1 is always LOST, regardless of M."""
    if f == 1:
        assert rfm_to_segment(1, 1, m) is Segment.LOST


@given(
    freq=st.integers(min_value=0, max_value=50),
    monetary=st.integers(min_value=0, max_value=10_000_000),
)
@settings(max_examples=50)
def test_forecast_non_negative(freq: int, monetary: int) -> None:
    """CLV forecast is always >= 0 regardless of input."""
    if freq == 0 and monetary > 0:
        return  # invalid input — schema rejects it elsewhere
    s = make_score(
        customer_id="C-1",
        frequency=freq,
        monetary_vnd=monetary if freq > 0 else 0,
        r_score=3,
        f_score=3,
        m_score=3,
    )
    [f] = forecast([s], {"C-1": Segment.LOYAL_CUSTOMERS}, window_days=180)
    assert f.forecast_vnd >= 0
    assert f.historical_aov_vnd >= 0


@given(
    scores_input=st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=5),
            st.integers(min_value=1, max_value=5),
            st.integers(min_value=1, max_value=5),
        ),
        min_size=1,
        max_size=20,
    ),
)
@settings(max_examples=30)
def test_classify_all_one_segment_per_customer(scores_input: list) -> None:  # type: ignore[type-arg]
    """``classify_all`` returns exactly one segment per input score."""
    scores = [
        make_score(customer_id=f"C-{i}", r_score=r, f_score=f, m_score=m)
        for i, (r, f, m) in enumerate(scores_input)
    ]
    out = classify_all(scores)
    assert len(out) == len(scores)
    for cid in (s.customer_id for s in scores):
        assert cid in out


@given(
    rfm=st.tuples(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
)
@settings(max_examples=125)
def test_forecast_lifetime_matches_segment(rfm: tuple[int, int, int]) -> None:
    """The forecast's ``expected_lifetime_days`` matches the segment's lookup value."""
    r, f, m = rfm
    seg = rfm_to_segment(r, f, m)
    s = make_score(
        customer_id="C-1", frequency=3, monetary_vnd=600_000, r_score=r, f_score=f, m_score=m
    )
    [out] = forecast([s], {"C-1": seg}, window_days=180)
    assert out.segment is seg
