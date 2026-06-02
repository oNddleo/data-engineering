"""CLV forecast."""

from __future__ import annotations

import pytest

from clvseg.clv import forecast, top_clv, total_clv_by_segment
from clvseg.schema import Segment

from ._fixtures import make_score


def test_forecast_zero_frequency_zero_clv():
    """No orders → no CLV."""
    s = make_score(customer_id="C-1", frequency=0, monetary_vnd=0, r_score=1, f_score=1, m_score=1)
    assignments = {"C-1": Segment.LOST}
    [f] = forecast([s], assignments, window_days=180)
    assert f.historical_aov_vnd == 0
    assert f.forecast_vnd == 0


def test_forecast_aov_computed():
    s = make_score(
        customer_id="C-1", frequency=5, monetary_vnd=1_000_000, r_score=5, f_score=3, m_score=4
    )
    assignments = {"C-1": Segment.LOYAL_CUSTOMERS}
    [f] = forecast([s], assignments, window_days=180)
    assert f.historical_aov_vnd == 200_000  # 1M / 5


def test_forecast_uses_segment_lifetime():
    """CHAMPIONS gets 1095-day expected lifetime, LOYAL gets 730."""
    s_champ = make_score(customer_id="C-CH", frequency=10, monetary_vnd=2_000_000)
    s_loyal = make_score(customer_id="C-LO", frequency=10, monetary_vnd=2_000_000)
    assignments = {"C-CH": Segment.CHAMPIONS, "C-LO": Segment.LOYAL_CUSTOMERS}
    fs = forecast([s_champ, s_loyal], assignments, window_days=180)
    champ_forecast = next(f for f in fs if f.customer_id == "C-CH")
    loyal_forecast = next(f for f in fs if f.customer_id == "C-LO")
    # Champion expected_lifetime > Loyal expected_lifetime, so champion CLV > loyal CLV.
    assert champ_forecast.forecast_vnd > loyal_forecast.forecast_vnd
    assert champ_forecast.expected_lifetime_days == 1095
    assert loyal_forecast.expected_lifetime_days == 730


def test_forecast_lost_segment_zero_lifetime_zero_clv():
    s = make_score(
        customer_id="C-1", frequency=5, monetary_vnd=500_000, r_score=1, f_score=1, m_score=1
    )
    assignments = {"C-1": Segment.LOST}
    [f] = forecast([s], assignments, window_days=180)
    assert f.expected_lifetime_days == 0
    assert f.forecast_vnd == 0


def test_forecast_validates_window():
    with pytest.raises(ValueError):
        forecast([], {}, window_days=0)


def test_forecast_custom_lifetime_map_used():
    """Caller-supplied lifetime map overrides the default."""
    s = make_score(customer_id="C-1", frequency=4, monetary_vnd=400_000)
    assignments = {"C-1": Segment.CHAMPIONS}
    custom = {Segment.CHAMPIONS: 100}  # 100-day lifetime overrides 1095
    [f] = forecast([s], assignments, window_days=180, lifetime_days=custom)
    assert f.expected_lifetime_days == 100


def test_forecast_unknown_customer_assignment_defaults_lost():
    """A score whose customer isn't in ``assignments`` falls back to LOST."""
    s = make_score(customer_id="C-1", frequency=5, monetary_vnd=500_000)
    [f] = forecast([s], {}, window_days=180)
    assert f.segment is Segment.LOST
    assert f.forecast_vnd == 0


def test_total_clv_by_segment_rolls_up():
    s1 = make_score(customer_id="C-1", frequency=5, monetary_vnd=1_000_000)
    s2 = make_score(customer_id="C-2", frequency=10, monetary_vnd=3_000_000)
    s3 = make_score(customer_id="C-3", frequency=2, monetary_vnd=200_000)
    assignments = {
        "C-1": Segment.CHAMPIONS,
        "C-2": Segment.CHAMPIONS,
        "C-3": Segment.HIBERNATING,
    }
    fs = forecast([s1, s2, s3], assignments, window_days=180)
    rollup = total_clv_by_segment(fs)
    assert rollup[Segment.CHAMPIONS] > rollup[Segment.HIBERNATING]
    assert set(rollup) == set(Segment)
    # Zero-fill for absent segments.
    assert rollup[Segment.LOST] == 0


def test_top_clv_orders_by_forecast_desc():
    s1 = make_score(customer_id="C-LOW", frequency=2, monetary_vnd=100_000)
    s2 = make_score(customer_id="C-HIGH", frequency=10, monetary_vnd=5_000_000)
    s3 = make_score(customer_id="C-MID", frequency=5, monetary_vnd=1_000_000)
    assignments = {sid: Segment.CHAMPIONS for sid in ("C-LOW", "C-HIGH", "C-MID")}
    fs = forecast([s1, s2, s3], assignments, window_days=180)
    top = top_clv(fs, n=3)
    assert top[0].customer_id == "C-HIGH"
    assert top[-1].customer_id == "C-LOW"


def test_top_clv_validates_n():
    with pytest.raises(ValueError):
        top_clv([], n=0)


def test_top_clv_limit_respected():
    scores = [
        make_score(customer_id=f"C-{i}", frequency=5, monetary_vnd=1_000_000) for i in range(10)
    ]
    assignments = {f"C-{i}": Segment.CHAMPIONS for i in range(10)}
    fs = forecast(scores, assignments, window_days=180)
    assert len(top_clv(fs, n=3)) == 3
