"""Hypothesis property tests for shipping pipeline."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnship.pricing import _weight_surcharge, calculate_fee
from vnship.schema import Carrier, ServiceType, ShipmentRequest, ZoneType


@given(st.integers(min_value=1, max_value=50_000))
@settings(max_examples=200)
def test_weight_surcharge_non_negative(weight_g: int) -> None:
    assert _weight_surcharge(weight_g, per_500g=2_500) >= 0


@given(st.integers(min_value=1_001, max_value=50_000))
@settings(max_examples=200)
def test_weight_surcharge_monotone(weight_g: int) -> None:
    """Heavier shipment never pays less surcharge."""
    s1 = _weight_surcharge(weight_g, per_500g=2_500)
    s2 = _weight_surcharge(weight_g + 1, per_500g=2_500)
    assert s2 >= s1


@given(
    st.integers(min_value=100, max_value=20_000),
    st.integers(min_value=0, max_value=5_000_000),
    st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_total_equals_sum_of_parts(weight_g: int, cod: int, fragile: bool) -> None:
    req = ShipmentRequest(
        carrier=Carrier.GHN,
        service=ServiceType.STANDARD,
        zone=ZoneType.INNER_CITY,
        weight_g=weight_g,
        declared_value_vnd=max(cod, 1),
        cod_amount_vnd=cod,
        is_fragile=fragile,
    )
    r = calculate_fee(req)
    assert r.total_fee_vnd == (
        r.base_fee_vnd + r.weight_surcharge_vnd + r.cod_fee_vnd + r.fragile_surcharge_vnd
    )


@given(st.integers(min_value=100, max_value=5_000_000))
@settings(max_examples=100)
def test_cod_fee_monotone(cod: int) -> None:
    """Higher COD → higher or equal COD fee."""
    req1 = ShipmentRequest(
        carrier=Carrier.GHN,
        service=ServiceType.STANDARD,
        zone=ZoneType.INNER_CITY,
        weight_g=500,
        declared_value_vnd=5_000_000,
        cod_amount_vnd=cod,
        is_fragile=False,
    )
    req2 = ShipmentRequest(
        carrier=Carrier.GHN,
        service=ServiceType.STANDARD,
        zone=ZoneType.INNER_CITY,
        weight_g=500,
        declared_value_vnd=5_000_000,
        cod_amount_vnd=cod + 1,
        is_fragile=False,
    )
    assert calculate_fee(req2).cod_fee_vnd >= calculate_fee(req1).cod_fee_vnd
