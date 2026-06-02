"""Unit tests for petroleum pricing."""

from __future__ import annotations

import pytest

from vnpetro.pricing import calculate_retail_price
from vnpetro.schema import FuelType, PriceInput, PriceRegion


def _inp(
    fuel_type: FuelType = FuelType.RON95_III,
    region: PriceRegion = PriceRegion.SOUTH,
    cif: float = 85.0,
    usd_to_vnd: float = 24_500.0,
    psf: float = 0.0,
) -> PriceInput:
    return PriceInput(
        fuel_type=fuel_type,
        region=region,
        cif_price_usd_per_barrel=cif,
        usd_to_vnd=usd_to_vnd,
        stabilisation_fund_vnd_per_litre=psf,
    )


class TestValidation:
    def test_negative_cif_raises(self) -> None:
        with pytest.raises(ValueError):
            _inp(cif=-1.0)

    def test_zero_usd_to_vnd_raises(self) -> None:
        with pytest.raises(ValueError):
            _inp(usd_to_vnd=0.0)


class TestPricing:
    def test_retail_price_positive(self) -> None:
        b = calculate_retail_price(_inp())
        assert b.retail_price_vnd_per_litre > 0

    def test_diesel_no_sct(self) -> None:
        b = calculate_retail_price(_inp(fuel_type=FuelType.DIESEL_005))
        assert b.sct_vnd == pytest.approx(0.0)

    def test_gasoline_has_sct(self) -> None:
        b = calculate_retail_price(_inp())
        assert b.sct_vnd > 0

    def test_ept_correct_ron95(self) -> None:
        b = calculate_retail_price(_inp())
        assert b.ept_vnd == pytest.approx(3_800.0)

    def test_ept_correct_diesel(self) -> None:
        b = calculate_retail_price(_inp(fuel_type=FuelType.DIESEL_005))
        assert b.ept_vnd == pytest.approx(1_500.0)

    def test_highlands_more_expensive_than_south(self) -> None:
        b_south = calculate_retail_price(_inp(region=PriceRegion.SOUTH))
        b_highlands = calculate_retail_price(_inp(region=PriceRegion.HIGHLANDS))
        assert b_highlands.retail_price_vnd_per_litre > b_south.retail_price_vnd_per_litre

    def test_north_more_expensive_than_south(self) -> None:
        b_south = calculate_retail_price(_inp(region=PriceRegion.SOUTH))
        b_north = calculate_retail_price(_inp(region=PriceRegion.NORTH))
        assert b_north.retail_price_vnd_per_litre > b_south.retail_price_vnd_per_litre

    def test_higher_cif_higher_retail(self) -> None:
        b_low = calculate_retail_price(_inp(cif=70.0))
        b_high = calculate_retail_price(_inp(cif=100.0))
        assert b_high.retail_price_vnd_per_litre > b_low.retail_price_vnd_per_litre

    def test_psf_negative_reduces_price(self) -> None:
        b0 = calculate_retail_price(_inp(psf=0.0))
        b_neg = calculate_retail_price(_inp(psf=-300.0))
        assert b_neg.retail_price_vnd_per_litre < b0.retail_price_vnd_per_litre

    def test_e5_lower_ept_than_ron95(self) -> None:
        b_ron95 = calculate_retail_price(_inp(fuel_type=FuelType.RON95_III))
        b_e5 = calculate_retail_price(_inp(fuel_type=FuelType.E5_RON92))
        assert b_e5.ept_vnd < b_ron95.ept_vnd

    def test_retail_price_rounded_multiple_of_10(self) -> None:
        b = calculate_retail_price(_inp())
        assert b.retail_price_rounded % 10 == 0

    def test_vat_on_base_plus_taxes(self) -> None:
        b = calculate_retail_price(_inp())
        expected_vat_base = b.base_price_vnd + b.sct_vnd + b.ept_vnd
        assert b.vat_vnd == pytest.approx(expected_vat_base * 0.10, rel=1e-4)

    def test_realistic_ron95_price_range(self) -> None:
        # RON95 at 85 USD/barrel with USD/VND = 24,500 should be roughly 20,000-28,000 VND/L
        b = calculate_retail_price(_inp())
        assert 15_000 < b.retail_price_vnd_per_litre < 35_000

    def test_all_fuels_price_ok(self) -> None:
        for ft in FuelType:
            b = calculate_retail_price(_inp(fuel_type=ft))
            assert b.retail_price_vnd_per_litre > 0
