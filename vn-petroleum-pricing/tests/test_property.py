"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnpetro.pricing import calculate_retail_price
from vnpetro.schema import FuelType, PriceInput, PriceRegion


@given(
    st.floats(min_value=40.0, max_value=150.0, allow_nan=False),
    st.floats(min_value=20_000.0, max_value=30_000.0, allow_nan=False),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_retail_always_positive(cif: float, usd_to_vnd: float) -> None:
    inp = PriceInput(
        fuel_type=FuelType.RON95_III,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=cif,
        usd_to_vnd=usd_to_vnd,
    )
    b = calculate_retail_price(inp)
    assert b.retail_price_vnd_per_litre > 0


@given(st.floats(min_value=40.0, max_value=150.0, allow_nan=False))
@settings(max_examples=100)
def test_higher_cif_higher_retail_monotone(cif: float) -> None:
    inp1 = PriceInput(
        fuel_type=FuelType.RON95_III,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=cif,
        usd_to_vnd=24_500.0,
    )
    inp2 = PriceInput(
        fuel_type=FuelType.RON95_III,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=cif + 1.0,
        usd_to_vnd=24_500.0,
    )
    b1 = calculate_retail_price(inp1)
    b2 = calculate_retail_price(inp2)
    assert b2.retail_price_vnd_per_litre > b1.retail_price_vnd_per_litre


@given(st.floats(min_value=40.0, max_value=150.0, allow_nan=False))
@settings(max_examples=100)
def test_retail_rounded_multiple_of_10(cif: float) -> None:
    inp = PriceInput(
        fuel_type=FuelType.RON95_III,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=cif,
        usd_to_vnd=24_500.0,
    )
    b = calculate_retail_price(inp)
    assert b.retail_price_rounded % 10 == 0


@given(st.floats(min_value=40.0, max_value=150.0, allow_nan=False))
@settings(max_examples=100)
def test_diesel_sct_always_zero(cif: float) -> None:
    inp = PriceInput(
        fuel_type=FuelType.DIESEL_005,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=cif,
        usd_to_vnd=24_500.0,
    )
    b = calculate_retail_price(inp)
    assert b.sct_vnd == 0.0
