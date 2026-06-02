"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vncoffee.pricing import price_lot
from vncoffee.schema import CoffeeGrade, CoffeeSpecies, ContractType, ExportLot, Incoterm


@given(
    st.floats(min_value=100.0, max_value=10_000.0, allow_nan=False),
    st.floats(min_value=-200.0, max_value=200.0, allow_nan=False),
    st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_fob_total_equals_price_times_volume(futures: float, diff: float, volume: float) -> None:
    # Skip if resulting price would be <= 0 (not a valid business case)
    if futures + diff <= 0:
        return
    lot = ExportLot(
        lot_id="L",
        species=CoffeeSpecies.ROBUSTA,
        grade=CoffeeGrade.R1,
        contract=ContractType.DIFFERENTIAL,
        incoterm=Incoterm.FOB,
        volume_mt=volume,
        futures_price_usd_mt=futures,
        differential_usd_mt=diff,
    )
    p = price_lot(lot)
    # total_fob is computed from unrounded fob_per_mt; fob_price_usd_mt is rounded to 2dp
    # so allow rounding error up to 0.01 * volume
    import math

    assert math.isclose(p.total_fob_usd, p.fob_price_usd_mt * volume, abs_tol=0.01 * volume + 1)


@given(st.floats(min_value=500.0, max_value=10_000.0, allow_nan=False))
@settings(max_examples=100)
def test_arabica_a1_premium_over_r1(base: float) -> None:
    """Arabica A1 always prices higher than Robusta R1 at same base."""
    r1 = ExportLot(
        lot_id="R",
        species=CoffeeSpecies.ROBUSTA,
        grade=CoffeeGrade.R1,
        contract=ContractType.FIXED_PRICE,
        incoterm=Incoterm.FOB,
        volume_mt=100.0,
        fixed_price_usd_mt=base,
    )
    a1 = ExportLot(
        lot_id="A",
        species=CoffeeSpecies.ARABICA,
        grade=CoffeeGrade.A1,
        contract=ContractType.FIXED_PRICE,
        incoterm=Incoterm.FOB,
        volume_mt=100.0,
        fixed_price_usd_mt=base,
    )
    assert price_lot(a1).fob_price_usd_mt > price_lot(r1).fob_price_usd_mt


@given(st.floats(min_value=1_000.0, max_value=5_000.0, allow_nan=False))
@settings(max_examples=100)
def test_grade_monotone_robusta(base: float) -> None:
    """R1 ≥ R2 ≥ R3 FOB price at same futures."""
    grades = [CoffeeGrade.R1, CoffeeGrade.R2, CoffeeGrade.R3]
    prices = [
        price_lot(
            ExportLot(
                lot_id="L",
                species=CoffeeSpecies.ROBUSTA,
                grade=g,
                contract=ContractType.DIFFERENTIAL,
                incoterm=Incoterm.FOB,
                volume_mt=10.0,
                futures_price_usd_mt=base,
            )
        ).fob_price_usd_mt
        for g in grades
    ]
    assert prices[0] >= prices[1] >= prices[2]
