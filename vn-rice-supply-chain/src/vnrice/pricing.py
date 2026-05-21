"""Export FOB pricing for milled rice.

Reference prices (USD/MT) based on 2024 Vietnam export prices.
Broken spec affects the price (less broken = higher price).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnrice.milling import MilledLot

from vnrice.schema import MilledRiceSpec, RiceVariety

# Base FOB prices USD/MT at 5% broken
_BASE_FOB: dict[RiceVariety, float] = {
    RiceVariety.JASMINE: 650.0,
    RiceVariety.IR50404: 480.0,
    RiceVariety.ST25: 900.0,
    RiceVariety.OM18: 520.0,
    RiceVariety.GLUTINOUS: 580.0,
}

# Price adjustment vs 5% broken (USD/MT)
_BROKEN_ADJ: dict[MilledRiceSpec, float] = {
    MilledRiceSpec.PERCENT_5: 0.0,
    MilledRiceSpec.PERCENT_10: -15.0,
    MilledRiceSpec.PERCENT_15: -30.0,
    MilledRiceSpec.PERCENT_25: -55.0,
    MilledRiceSpec.PERCENT_100: -180.0,  # broken rice / tam
}

_USD_TO_VND = 24_500.0  # approximate


@dataclass(frozen=True, slots=True)
class ExportQuote:
    milled: MilledLot
    fob_price_usd_mt: float
    total_fob_usd: float
    paddy_cost_vnd: float
    paddy_cost_usd: float
    gross_margin_usd: float


def quote_export(milled: MilledLot, freight_usd_mt: float = 0.0) -> ExportQuote:
    """Produce an FOB export quote from a milled lot."""
    variety = milled.paddy.variety
    spec = milled.broken_spec

    base_fob = _BASE_FOB[variety]
    broken_adj = _BROKEN_ADJ[spec]
    fob_per_mt = base_fob + broken_adj

    total_fob = fob_per_mt * milled.white_rice_mt

    # Paddy input cost
    paddy_cost_vnd = milled.paddy.weight_mt * 1000.0 * milled.paddy.price_vnd_per_kg
    paddy_cost_usd = paddy_cost_vnd / _USD_TO_VND

    # Gross margin: FOB revenue - paddy cost - milling cost - freight
    freight_total = freight_usd_mt * milled.white_rice_mt
    gross_margin = total_fob - paddy_cost_usd - milled.milling_cost_usd - freight_total

    return ExportQuote(
        milled=milled,
        fob_price_usd_mt=round(fob_per_mt, 2),
        total_fob_usd=round(total_fob, 2),
        paddy_cost_vnd=round(paddy_cost_vnd, 0),
        paddy_cost_usd=round(paddy_cost_usd, 2),
        gross_margin_usd=round(gross_margin, 2),
    )
