"""Unit tests for milling module."""

from __future__ import annotations

import pytest

from vnrice.milling import mill
from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety


def _lot(
    variety: RiceVariety = RiceVariety.JASMINE,
    grade: PaddyGrade = PaddyGrade.GRADE_1,
    weight_mt: float = 100.0,
    moisture_pct: float = 14.0,
    price_vnd: float = 7_500.0,
) -> PaddyLot:
    return PaddyLot(
        lot_id="LOT-001",
        variety=variety,
        grade=grade,
        weight_mt=weight_mt,
        moisture_pct=moisture_pct,
        price_vnd_per_kg=price_vnd,
    )


class TestSchemaValidation:
    def test_empty_lot_id_raises(self) -> None:
        with pytest.raises(ValueError):
            PaddyLot(
                lot_id="",
                variety=RiceVariety.JASMINE,
                grade=PaddyGrade.GRADE_1,
                weight_mt=100.0,
                moisture_pct=14.0,
                price_vnd_per_kg=7500.0,
            )

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError):
            _lot(weight_mt=-1.0)

    def test_moisture_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            _lot(moisture_pct=5.0)

    def test_negative_price_raises(self) -> None:
        with pytest.raises(ValueError):
            _lot(price_vnd=-1.0)


class TestMillingYield:
    def test_jasmine_grade1_yield(self) -> None:
        m = mill(_lot(), MilledRiceSpec.PERCENT_5)
        assert m.milling_yield_pct == pytest.approx(65.0)

    def test_ir50404_higher_yield(self) -> None:
        m = mill(_lot(variety=RiceVariety.IR50404), MilledRiceSpec.PERCENT_5)
        assert m.milling_yield_pct == pytest.approx(68.0)

    def test_grade2_lower_yield(self) -> None:
        m1 = mill(_lot(grade=PaddyGrade.GRADE_1), MilledRiceSpec.PERCENT_5)
        m2 = mill(_lot(grade=PaddyGrade.GRADE_2), MilledRiceSpec.PERCENT_5)
        assert m2.milling_yield_pct < m1.milling_yield_pct

    def test_grade3_lowest_yield(self) -> None:
        m1 = mill(_lot(grade=PaddyGrade.GRADE_1), MilledRiceSpec.PERCENT_5)
        m3 = mill(_lot(grade=PaddyGrade.GRADE_3), MilledRiceSpec.PERCENT_5)
        assert m3.milling_yield_pct < m1.milling_yield_pct

    def test_dry_weight_at_standard_moisture(self) -> None:
        m = mill(_lot(moisture_pct=14.0, weight_mt=100.0), MilledRiceSpec.PERCENT_5)
        assert m.dry_weight_mt == pytest.approx(100.0, rel=1e-3)

    def test_dry_weight_reduced_for_excess_moisture(self) -> None:
        m = mill(_lot(moisture_pct=20.0, weight_mt=100.0), MilledRiceSpec.PERCENT_5)
        assert m.dry_weight_mt < 100.0

    def test_white_rice_plus_bran_equals_dry_weight(self) -> None:
        m = mill(_lot(moisture_pct=16.0, weight_mt=200.0), MilledRiceSpec.PERCENT_10)
        assert m.white_rice_mt + m.bran_mt == pytest.approx(m.dry_weight_mt, rel=1e-4)

    def test_milling_cost_proportional_to_weight(self) -> None:
        m1 = mill(_lot(weight_mt=100.0), MilledRiceSpec.PERCENT_5)
        m2 = mill(_lot(weight_mt=200.0), MilledRiceSpec.PERCENT_5)
        assert m2.milling_cost_usd == pytest.approx(m1.milling_cost_usd * 2.0, rel=1e-3)


class TestPricing:
    def test_st25_premium_over_ir50404(self) -> None:
        from vnrice.pricing import quote_export

        q1 = quote_export(mill(_lot(variety=RiceVariety.ST25), MilledRiceSpec.PERCENT_5))
        q2 = quote_export(mill(_lot(variety=RiceVariety.IR50404), MilledRiceSpec.PERCENT_5))
        assert q1.fob_price_usd_mt > q2.fob_price_usd_mt

    def test_less_broken_higher_price(self) -> None:
        from vnrice.pricing import quote_export

        q5 = quote_export(mill(_lot(), MilledRiceSpec.PERCENT_5))
        q25 = quote_export(mill(_lot(), MilledRiceSpec.PERCENT_25))
        assert q5.fob_price_usd_mt > q25.fob_price_usd_mt

    def test_total_fob_positive(self) -> None:
        from vnrice.pricing import quote_export

        q = quote_export(mill(_lot(), MilledRiceSpec.PERCENT_5))
        assert q.total_fob_usd > 0
