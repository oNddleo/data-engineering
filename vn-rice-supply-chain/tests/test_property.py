"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnrice.milling import mill
from vnrice.pricing import quote_export
from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety


@given(
    st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
    st.floats(min_value=10.0, max_value=25.0, allow_nan=False),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_white_rice_plus_bran_eq_dry(weight: float, moisture: float) -> None:
    lot = PaddyLot(
        lot_id="L",
        variety=RiceVariety.JASMINE,
        grade=PaddyGrade.GRADE_1,
        weight_mt=weight,
        moisture_pct=moisture,
        price_vnd_per_kg=7500.0,
    )
    m = mill(lot, MilledRiceSpec.PERCENT_5)
    import math

    assert math.isclose(m.white_rice_mt + m.bran_mt, m.dry_weight_mt, rel_tol=1e-4)


@given(st.floats(min_value=10.0, max_value=500.0, allow_nan=False))
@settings(max_examples=100)
def test_dry_weight_never_exceeds_wet(weight: float) -> None:
    lot = PaddyLot(
        lot_id="L",
        variety=RiceVariety.OM18,
        grade=PaddyGrade.GRADE_2,
        weight_mt=weight,
        moisture_pct=18.0,
        price_vnd_per_kg=7000.0,
    )
    m = mill(lot, MilledRiceSpec.PERCENT_10)
    assert m.dry_weight_mt <= weight


@given(st.floats(min_value=50.0, max_value=200.0, allow_nan=False))
@settings(max_examples=100)
def test_total_fob_positive(weight: float) -> None:
    lot = PaddyLot(
        lot_id="L",
        variety=RiceVariety.IR50404,
        grade=PaddyGrade.GRADE_1,
        weight_mt=weight,
        moisture_pct=14.0,
        price_vnd_per_kg=6500.0,
    )
    q = quote_export(mill(lot, MilledRiceSpec.PERCENT_5))
    assert q.total_fob_usd > 0
    assert q.fob_price_usd_mt > 0
