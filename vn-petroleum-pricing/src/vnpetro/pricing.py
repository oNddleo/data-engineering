"""Vietnam petroleum retail price calculator.

Formula (Decree 95/2021/ND-CP):
  Base price (Gia co so) = CIF + import tariff + VAT + import costs
  Retail price = Base price + SCT + EPT + VAT on SCT+EPT + dealer margin + PSF

All prices in VND/litre.

Tax rates (as of 2024):
  - Import tariff: 8% for most ASEAN sourced fuels (0% from Thailand/Singapore)
  - Special Consumption Tax (SCT): 10% for gasoline, 0% for diesel
  - Environmental Protection Tax (EPT): 3,800 VND/L for gasoline, 1,500 for diesel
  - VAT: 10%
  - Dealer margin: 1,250 VND/L
"""

from __future__ import annotations

from dataclasses import dataclass

from vnpetro.schema import FuelType, PriceInput, PriceRegion

# Conversion: 1 barrel = 159 litres (petroleum industry standard = 158.987, use 159)
_BARREL_TO_LITRES = 159.0

# Import tariff rates (fraction)
_IMPORT_TARIFF: dict[FuelType, float] = {
    FuelType.RON95_III: 0.08,
    FuelType.RON92_II: 0.08,
    FuelType.DIESEL_005: 0.05,
    FuelType.KEROSENE: 0.07,
    FuelType.E5_RON92: 0.08,
}

# Special Consumption Tax (fraction of pre-SCT price)
_SCT_RATE: dict[FuelType, float] = {
    FuelType.RON95_III: 0.10,
    FuelType.RON92_II: 0.10,
    FuelType.DIESEL_005: 0.0,
    FuelType.KEROSENE: 0.0,
    FuelType.E5_RON92: 0.08,  # E5 gets reduced rate
}

# Environmental Protection Tax (VND/litre) - Decree 44/2023/QD-TTg
_EPT_VND_PER_LITRE: dict[FuelType, float] = {
    FuelType.RON95_III: 3_800.0,
    FuelType.RON92_II: 3_800.0,
    FuelType.DIESEL_005: 1_500.0,
    FuelType.KEROSENE: 1_000.0,
    FuelType.E5_RON92: 2_000.0,  # E5 lower EPT
}

# Regional transport surcharge (VND/litre)
_REGIONAL_SURCHARGE: dict[PriceRegion, float] = {
    PriceRegion.SOUTH: 0.0,  # base region (Ho Chi Minh City is import hub)
    PriceRegion.NORTH: 150.0,
    PriceRegion.CENTRAL: 100.0,
    PriceRegion.HIGHLANDS: 400.0,
}

# Dealer profit margin (VND/litre)
_DEALER_MARGIN: float = 1_250.0

# VAT rate
_VAT_RATE: float = 0.10

# Import cost (USD/tonne) → convert to VND/litre (approx 0.75 kg/L for gasoline)
_IMPORT_COST_USD_PER_TONNE: float = 15.0  # freight + insurance + port
_GASOLINE_KG_PER_LITRE: float = 0.74  # RON 92/95 density


@dataclass(frozen=True, slots=True)
class PriceBreakdown:
    """Full retail price breakdown (VND/litre)."""

    fuel_type: FuelType
    region: PriceRegion
    cif_vnd_per_litre: float
    import_tariff_vnd: float
    import_cost_vnd: float
    base_price_vnd: float  # CIF + tariff + import costs
    sct_vnd: float  # Special Consumption Tax
    ept_vnd: float  # Environmental Protection Tax
    vat_vnd: float  # VAT on (base + SCT + EPT)
    dealer_margin_vnd: float
    regional_surcharge_vnd: float
    stabilisation_fund_vnd: float
    retail_price_vnd_per_litre: float

    @property
    def retail_price_rounded(self) -> int:
        """Retail price rounded to nearest 10 VND (regulatory requirement)."""
        return round(self.retail_price_vnd_per_litre / 10) * 10


def calculate_retail_price(inp: PriceInput) -> PriceBreakdown:
    """Compute full retail price breakdown for a petroleum product."""
    ft = inp.fuel_type
    region = inp.region

    # Step 1: CIF → VND/litre
    cif_vnd_litre = (inp.cif_price_usd_per_barrel / _BARREL_TO_LITRES) * inp.usd_to_vnd

    # Step 2: Import tariff
    tariff = cif_vnd_litre * _IMPORT_TARIFF[ft]

    # Step 3: Import cost (freight/insurance)
    import_cost = (_IMPORT_COST_USD_PER_TONNE / (1_000 / _GASOLINE_KG_PER_LITRE)) * inp.usd_to_vnd

    # Step 4: Base price
    base = cif_vnd_litre + tariff + import_cost

    # Step 5: Special Consumption Tax on base
    sct = base * _SCT_RATE[ft]

    # Step 6: Environmental Protection Tax (flat per litre)
    ept = _EPT_VND_PER_LITRE[ft]

    # Step 7: VAT on (base + sct + ept)
    vat = (base + sct + ept) * _VAT_RATE

    # Step 8: Dealer margin + regional surcharge + PSF
    dealer = _DEALER_MARGIN
    regional = _REGIONAL_SURCHARGE[region]
    psf = inp.stabilisation_fund_vnd_per_litre  # can be negative (extraction) or positive

    # Step 9: Retail price
    retail = base + sct + ept + vat + dealer + regional + psf

    return PriceBreakdown(
        fuel_type=ft,
        region=region,
        cif_vnd_per_litre=round(cif_vnd_litre, 2),
        import_tariff_vnd=round(tariff, 2),
        import_cost_vnd=round(import_cost, 2),
        base_price_vnd=round(base, 2),
        sct_vnd=round(sct, 2),
        ept_vnd=round(ept, 2),
        vat_vnd=round(vat, 2),
        dealer_margin_vnd=round(dealer, 2),
        regional_surcharge_vnd=round(regional, 2),
        stabilisation_fund_vnd=round(psf, 2),
        retail_price_vnd_per_litre=round(retail, 2),
    )
