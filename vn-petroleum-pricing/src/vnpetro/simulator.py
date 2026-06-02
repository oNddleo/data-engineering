"""Synthetic petroleum price scenario generator."""

from __future__ import annotations

import random
from dataclasses import dataclass

from vnpetro.pricing import PriceBreakdown, calculate_retail_price
from vnpetro.schema import FuelType, PriceInput, PriceRegion


@dataclass(frozen=True, slots=True)
class SimStats:
    n_scenarios: int
    avg_retail_vnd_per_litre: dict[str, float]
    max_retail_vnd_per_litre: float
    min_retail_vnd_per_litre: float


def generate(
    n: int = 50,
    seed: int = 0,
    # Brent crude price range (USD/barrel)
    cif_low: float = 70.0,
    cif_high: float = 110.0,
    usd_to_vnd: float = 24_500.0,
) -> list[PriceBreakdown]:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = random.Random(seed)
    results: list[PriceBreakdown] = []
    for _ in range(n):
        ft = rng.choice(list(FuelType))
        region = rng.choice(list(PriceRegion))
        cif = round(rng.uniform(cif_low, cif_high), 2)
        psf = round(rng.uniform(-300.0, 300.0), 0)
        inp = PriceInput(
            fuel_type=ft,
            region=region,
            cif_price_usd_per_barrel=cif,
            usd_to_vnd=usd_to_vnd,
            stabilisation_fund_vnd_per_litre=psf,
        )
        results.append(calculate_retail_price(inp))
    return results


def summarise(breakdowns: list[PriceBreakdown]) -> SimStats:
    if not breakdowns:
        return SimStats(
            n_scenarios=0,
            avg_retail_vnd_per_litre={},
            max_retail_vnd_per_litre=0.0,
            min_retail_vnd_per_litre=0.0,
        )
    by_fuel: dict[str, list[float]] = {}
    for b in breakdowns:
        key = b.fuel_type.value
        by_fuel.setdefault(key, []).append(b.retail_price_vnd_per_litre)
    avg = {k: round(sum(v) / len(v), 0) for k, v in by_fuel.items()}
    all_prices = [b.retail_price_vnd_per_litre for b in breakdowns]
    return SimStats(
        n_scenarios=len(breakdowns),
        avg_retail_vnd_per_litre=avg,
        max_retail_vnd_per_litre=max(all_prices),
        min_retail_vnd_per_litre=min(all_prices),
    )
