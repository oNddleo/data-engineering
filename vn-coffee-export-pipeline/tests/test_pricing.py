"""Unit tests for coffee export pricing."""

from __future__ import annotations

import pytest

from vncoffee.pricing import price_lot
from vncoffee.schema import (
    CoffeeGrade,
    CoffeeSpecies,
    ContractType,
    ExportLot,
    Incoterm,
)


def _differential_lot(
    grade: CoffeeGrade = CoffeeGrade.R1,
    futures: float = 2800.0,
    diff: float = 0.0,
    volume: float = 100.0,
    incoterm: Incoterm = Incoterm.FOB,
    freight: float = 0.0,
    insurance: float = 0.0,
) -> ExportLot:
    return ExportLot(
        lot_id="LOT-001",
        species=CoffeeSpecies.ROBUSTA,
        grade=grade,
        contract=ContractType.DIFFERENTIAL,
        incoterm=incoterm,
        volume_mt=volume,
        futures_price_usd_mt=futures,
        differential_usd_mt=diff,
        freight_usd_mt=freight,
        insurance_rate_pct=insurance,
    )


def _fixed_lot(
    grade: CoffeeGrade = CoffeeGrade.R1,
    fixed: float = 2800.0,
    volume: float = 100.0,
) -> ExportLot:
    return ExportLot(
        lot_id="LOT-002",
        species=CoffeeSpecies.ROBUSTA,
        grade=grade,
        contract=ContractType.FIXED_PRICE,
        incoterm=Incoterm.FOB,
        volume_mt=volume,
        fixed_price_usd_mt=fixed,
    )


class TestSchemaValidation:
    def test_empty_lot_id_raises(self) -> None:
        with pytest.raises(ValueError):
            ExportLot(
                lot_id="",
                species=CoffeeSpecies.ROBUSTA,
                grade=CoffeeGrade.R1,
                contract=ContractType.FIXED_PRICE,
                incoterm=Incoterm.FOB,
                volume_mt=100.0,
                fixed_price_usd_mt=2800.0,
            )

    def test_zero_volume_raises(self) -> None:
        with pytest.raises(ValueError):
            ExportLot(
                lot_id="L",
                species=CoffeeSpecies.ROBUSTA,
                grade=CoffeeGrade.R1,
                contract=ContractType.FIXED_PRICE,
                incoterm=Incoterm.FOB,
                volume_mt=0.0,
                fixed_price_usd_mt=2800.0,
            )

    def test_differential_without_futures_raises(self) -> None:
        with pytest.raises(ValueError, match="futures"):
            ExportLot(
                lot_id="L",
                species=CoffeeSpecies.ROBUSTA,
                grade=CoffeeGrade.R1,
                contract=ContractType.DIFFERENTIAL,
                incoterm=Incoterm.FOB,
                volume_mt=100.0,
            )

    def test_cif_without_freight_raises(self) -> None:
        with pytest.raises(ValueError, match="freight"):
            ExportLot(
                lot_id="L",
                species=CoffeeSpecies.ROBUSTA,
                grade=CoffeeGrade.R1,
                contract=ContractType.FIXED_PRICE,
                incoterm=Incoterm.CIF,
                volume_mt=100.0,
                fixed_price_usd_mt=2800.0,
            )


class TestPricing:
    def test_differential_no_grade_adj(self) -> None:
        p = price_lot(_differential_lot(futures=3000.0, diff=50.0))
        assert p.fob_price_usd_mt == pytest.approx(3050.0)
        assert p.total_fob_usd == pytest.approx(305_000.0)

    def test_grade_r2_discount(self) -> None:
        p1 = price_lot(_differential_lot(grade=CoffeeGrade.R1, futures=3000.0))
        p2 = price_lot(_differential_lot(grade=CoffeeGrade.R2, futures=3000.0))
        assert p2.fob_price_usd_mt < p1.fob_price_usd_mt
        assert p2.grade_adjustment_usd_mt == pytest.approx(-10.0)

    def test_arabica_premium(self) -> None:
        lot = ExportLot(
            lot_id="L",
            species=CoffeeSpecies.ARABICA,
            grade=CoffeeGrade.A1,
            contract=ContractType.FIXED_PRICE,
            incoterm=Incoterm.FOB,
            volume_mt=10.0,
            fixed_price_usd_mt=4000.0,
        )
        p = price_lot(lot)
        assert p.grade_adjustment_usd_mt == pytest.approx(200.0)
        assert p.fob_price_usd_mt == pytest.approx(4200.0)

    def test_fixed_price_total(self) -> None:
        p = price_lot(_fixed_lot(fixed=3000.0, volume=50.0))
        assert p.total_fob_usd == pytest.approx(150_000.0)

    def test_negative_differential(self) -> None:
        p = price_lot(_differential_lot(futures=3000.0, diff=-100.0))
        assert p.fob_price_usd_mt == pytest.approx(2900.0)

    def test_total_contract_fob(self) -> None:
        p = price_lot(_differential_lot(futures=3000.0))
        assert p.total_contract_usd == pytest.approx(p.total_fob_usd)
