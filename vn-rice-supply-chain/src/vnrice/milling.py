"""Paddy-to-milled-rice conversion with milling yield calculation.

Milling yield: how much white rice you get from paddy.
Typical range: 60-72% depending on variety and moisture.

Drying loss: excess moisture above 14% adds ~1% weight loss per 2% moisture.
"""

from __future__ import annotations

from dataclasses import dataclass

from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety

# Base milling yield per variety (%) at standard 14% moisture
_BASE_YIELD: dict[RiceVariety, float] = {
    RiceVariety.JASMINE: 65.0,
    RiceVariety.IR50404: 68.0,
    RiceVariety.ST25: 64.0,
    RiceVariety.OM18: 66.0,
    RiceVariety.GLUTINOUS: 62.0,
}

# Grade quality adjustment (percentage points)
_GRADE_ADJ: dict[PaddyGrade, float] = {
    PaddyGrade.GRADE_1: 0.0,
    PaddyGrade.GRADE_2: -2.0,
    PaddyGrade.GRADE_3: -4.0,
}

# Standard target moisture for export
_TARGET_MOISTURE = 14.0
_DRYING_FACTOR = 0.5  # % weight loss per 1% excess moisture


@dataclass(frozen=True, slots=True)
class MilledLot:
    paddy: PaddyLot
    dry_weight_mt: float  # after drying to 14%
    milling_yield_pct: float
    white_rice_mt: float
    bran_mt: float
    broken_spec: MilledRiceSpec
    milling_cost_usd: float


def mill(
    lot: PaddyLot, broken_spec: MilledRiceSpec, milling_cost_usd_per_mt: float = 8.0
) -> MilledLot:
    """Convert a paddy lot into milled white rice."""
    # Drying loss: reduce wet paddy to 14% moisture
    excess_moisture = max(0.0, lot.moisture_pct - _TARGET_MOISTURE)
    drying_loss_pct = excess_moisture * _DRYING_FACTOR
    dry_weight = lot.weight_mt * (1.0 - drying_loss_pct / 100.0)

    # Milling yield
    base_yield = _BASE_YIELD[lot.variety]
    grade_adj = _GRADE_ADJ[lot.grade]
    yield_pct = base_yield + grade_adj

    white_rice = dry_weight * yield_pct / 100.0
    bran = dry_weight - white_rice  # husk + bran

    milling_cost = dry_weight * milling_cost_usd_per_mt

    return MilledLot(
        paddy=lot,
        dry_weight_mt=round(dry_weight, 4),
        milling_yield_pct=round(yield_pct, 2),
        white_rice_mt=round(white_rice, 4),
        bran_mt=round(bran, 4),
        broken_spec=broken_spec,
        milling_cost_usd=round(milling_cost, 2),
    )
