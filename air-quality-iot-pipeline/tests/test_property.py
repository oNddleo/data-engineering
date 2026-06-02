"""Hypothesis properties — invariants of AQI math + aggregator."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from aqipipe.qcvn import aqi_for, band_for_aqi, station_aqi
from aqipipe.schema import Pollutant


@given(value_x10=st.integers(min_value=0, max_value=10_000_000))
@settings(max_examples=200)
def test_aqi_for_always_in_0_500(value_x10: int) -> None:
    """AQI output is always in [0, 500] for any non-negative concentration."""
    for poll in Pollutant:
        result = aqi_for(poll, value_x10)
        assert 0 <= result.aqi <= 500


@given(value_x10=st.integers(min_value=0, max_value=10_000_000))
@settings(max_examples=200)
def test_aqi_band_consistent_with_value(value_x10: int) -> None:
    """``band`` always corresponds to ``band_for_aqi(aqi)`` — the two paths agree."""
    for poll in Pollutant:
        result = aqi_for(poll, value_x10)
        assert result.band is band_for_aqi(result.aqi)


@given(
    v1=st.integers(min_value=0, max_value=5000),
    v2=st.integers(min_value=0, max_value=5000),
)
@settings(max_examples=100)
def test_aqi_monotonic_within_pollutant(v1: int, v2: int) -> None:
    """Higher concentration → higher (or equal) AQI for the same pollutant."""
    for poll in Pollutant:
        lo, hi = (v1, v2) if v1 <= v2 else (v2, v1)
        assert aqi_for(poll, lo).aqi <= aqi_for(poll, hi).aqi


@given(
    values=st.dictionaries(
        keys=st.sampled_from(list(Pollutant)),
        values=st.integers(min_value=0, max_value=10000),
        min_size=1,
        max_size=6,
    ),
)
@settings(max_examples=100)
def test_station_aqi_at_least_each_contribution(values: dict[Pollutant, int]) -> None:
    """Station AQI ≥ each per-pollutant AQI (max ≥ any individual)."""
    sa = station_aqi("S-1", values)
    for c in sa.contributions:
        assert sa.aqi >= c.aqi


@given(
    values=st.dictionaries(
        keys=st.sampled_from(list(Pollutant)),
        values=st.integers(min_value=0, max_value=10000),
        min_size=1,
        max_size=6,
    ),
)
@settings(max_examples=100)
def test_station_aqi_equals_max_contribution(values: dict[Pollutant, int]) -> None:
    """Station AQI = max over contributions."""
    sa = station_aqi("S-1", values)
    assert sa.aqi == max(c.aqi for c in sa.contributions)


@given(aqi=st.integers(min_value=0, max_value=500))
@settings(max_examples=50)
def test_band_for_aqi_is_total(aqi: int) -> None:
    """Every AQI in [0, 500] maps to exactly one band."""
    from aqipipe.qcvn import AQIBand

    band = band_for_aqi(aqi)
    assert isinstance(band, AQIBand)
