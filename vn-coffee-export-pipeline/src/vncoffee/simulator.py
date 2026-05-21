"""Synthetic coffee export lot generator."""

from __future__ import annotations

import random
from dataclasses import dataclass

from vncoffee.pricing import PricedLot, price_lot
from vncoffee.schema import (
    CoffeeGrade,
    CoffeeSpecies,
    ContractType,
    ExportLot,
    Incoterm,
)

# Realistic 2024 base prices USD/MT
_ROBUSTA_FUTURES = (2_500.0, 3_500.0)  # London LIFFE range
_ARABICA_FUTURES = (3_500.0, 5_500.0)  # ICE range
_ROBUSTA_GRADES = [CoffeeGrade.R1, CoffeeGrade.R2, CoffeeGrade.R3]
_ARABICA_GRADES = [CoffeeGrade.A1, CoffeeGrade.A2]


@dataclass(frozen=True, slots=True)
class SimStats:
    n_lots: int
    total_volume_mt: float
    total_value_usd: float
    avg_fob_usd_mt: float
    species_counts: dict[str, int]


def generate(n: int = 50, seed: int = 0) -> list[PricedLot]:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = random.Random(seed)
    results: list[PricedLot] = []
    for i in range(n):
        species = rng.choice(list(CoffeeSpecies))
        if species == CoffeeSpecies.ROBUSTA:
            grade = rng.choice(_ROBUSTA_GRADES)
            futures = rng.uniform(*_ROBUSTA_FUTURES)
        else:
            grade = rng.choice(_ARABICA_GRADES)
            futures = rng.uniform(*_ARABICA_FUTURES)

        contract = rng.choice(list(ContractType))
        incoterm = rng.choice(list(Incoterm))
        volume = round(rng.uniform(5.0, 500.0), 2)
        diff = round(rng.uniform(-50.0, 50.0), 2)
        freight = round(rng.uniform(30.0, 80.0), 2)

        if contract == ContractType.DIFFERENTIAL:
            lot = ExportLot(
                lot_id=f"LOT-{i+1:04d}",
                species=species,
                grade=grade,
                contract=contract,
                incoterm=incoterm if incoterm != Incoterm.CIF else Incoterm.FOB,
                volume_mt=volume,
                futures_price_usd_mt=round(futures, 2),
                differential_usd_mt=diff,
                freight_usd_mt=freight if incoterm == Incoterm.CIF else 0.0,
                insurance_rate_pct=0.3,
            )
        else:
            lot = ExportLot(
                lot_id=f"LOT-{i+1:04d}",
                species=species,
                grade=grade,
                contract=contract,
                incoterm=incoterm if incoterm != Incoterm.CIF else Incoterm.FOB,
                volume_mt=volume,
                fixed_price_usd_mt=round(futures + diff, 2),
                freight_usd_mt=freight if incoterm == Incoterm.CIF else 0.0,
                insurance_rate_pct=0.3,
            )
        results.append(price_lot(lot))
    return results


def summarise(lots: list[PricedLot]) -> SimStats:
    if not lots:
        return SimStats(
            n_lots=0,
            total_volume_mt=0.0,
            total_value_usd=0.0,
            avg_fob_usd_mt=0.0,
            species_counts={},
        )
    total_vol = sum(p.lot.volume_mt for p in lots)
    total_val = sum(p.total_contract_usd for p in lots)
    species_counts: dict[str, int] = {}
    for p in lots:
        k = p.lot.species.value
        species_counts[k] = species_counts.get(k, 0) + 1
    return SimStats(
        n_lots=len(lots),
        total_volume_mt=round(total_vol, 2),
        total_value_usd=round(total_val, 2),
        avg_fob_usd_mt=round(sum(p.fob_price_usd_mt for p in lots) / len(lots), 2),
        species_counts=species_counts,
    )
