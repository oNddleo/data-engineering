"""FOB/CIF pricing for VN coffee export lots."""

from __future__ import annotations

from dataclasses import dataclass

from vncoffee.schema import ContractType, ExportLot, Incoterm

# Grade quality premium/discount vs baseline (USD/MT)
_GRADE_DIFF: dict[str, float] = {
    "R1": 0.0,
    "R2": -10.0,
    "R3": -25.0,
    "A1": 200.0,  # specialty premium
    "A2": 80.0,
}


@dataclass(frozen=True, slots=True)
class PricedLot:
    lot: ExportLot
    fob_price_usd_mt: float
    grade_adjustment_usd_mt: float
    total_fob_usd: float
    freight_total_usd: float
    insurance_total_usd: float
    cif_price_usd_mt: float
    total_contract_usd: float


def price_lot(lot: ExportLot) -> PricedLot:
    """Compute FOB and CIF pricing for a coffee export lot."""
    # Step 1: base FOB price per MT
    if lot.contract == ContractType.DIFFERENTIAL:
        base_fob = lot.futures_price_usd_mt + lot.differential_usd_mt
    else:
        base_fob = lot.fixed_price_usd_mt

    # Step 2: grade quality adjustment
    grade_adj = _GRADE_DIFF.get(lot.grade.value, 0.0)
    fob_per_mt = base_fob + grade_adj

    # Step 3: total FOB value
    total_fob = fob_per_mt * lot.volume_mt

    # Step 4: CIF additions
    freight_total = lot.freight_usd_mt * lot.volume_mt
    insurance_total = total_fob * (lot.insurance_rate_pct / 100.0)

    if lot.incoterm == Incoterm.CIF:
        cif_per_mt = fob_per_mt + lot.freight_usd_mt + (insurance_total / lot.volume_mt)
        total_contract = total_fob + freight_total + insurance_total
    elif lot.incoterm == Incoterm.EXW:
        # Ex-works: subtract inland logistics (not modelled here — use FOB as proxy)
        cif_per_mt = fob_per_mt
        total_contract = total_fob
    else:
        cif_per_mt = fob_per_mt
        total_contract = total_fob

    return PricedLot(
        lot=lot,
        fob_price_usd_mt=round(fob_per_mt, 2),
        grade_adjustment_usd_mt=round(grade_adj, 2),
        total_fob_usd=round(total_fob, 2),
        freight_total_usd=round(freight_total, 2),
        insurance_total_usd=round(insurance_total, 2),
        cif_price_usd_mt=round(cif_per_mt, 4),
        total_contract_usd=round(total_contract, 2),
    )
