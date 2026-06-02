"""Synthetic paddy lot generator."""

from __future__ import annotations

import random
from dataclasses import dataclass

from vnrice.milling import mill
from vnrice.pricing import ExportQuote, quote_export
from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety


@dataclass(frozen=True, slots=True)
class SimStats:
    n_lots: int
    total_paddy_mt: float
    total_white_rice_mt: float
    avg_milling_yield_pct: float
    total_fob_usd: float
    total_gross_margin_usd: float


def generate(n: int = 50, seed: int = 0) -> list[ExportQuote]:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = random.Random(seed)
    results: list[ExportQuote] = []
    for i in range(n):
        variety = rng.choice(list(RiceVariety))
        grade = rng.choice(list(PaddyGrade))
        spec = rng.choice(list(MilledRiceSpec))
        weight = round(rng.uniform(10.0, 1000.0), 1)
        moisture = round(rng.uniform(12.0, 22.0), 1)
        price_vnd = round(rng.uniform(6_000.0, 9_000.0), 0)
        lot = PaddyLot(
            lot_id=f"LOT-{i+1:04d}",
            variety=variety,
            grade=grade,
            weight_mt=weight,
            moisture_pct=moisture,
            price_vnd_per_kg=price_vnd,
        )
        milled = mill(lot, spec)
        results.append(quote_export(milled))
    return results


def summarise(quotes: list[ExportQuote]) -> SimStats:
    if not quotes:
        return SimStats(0, 0.0, 0.0, 0.0, 0.0, 0.0)
    total_paddy = sum(q.milled.paddy.weight_mt for q in quotes)
    total_white = sum(q.milled.white_rice_mt for q in quotes)
    avg_yield = sum(q.milled.milling_yield_pct for q in quotes) / len(quotes)
    total_fob = sum(q.total_fob_usd for q in quotes)
    total_margin = sum(q.gross_margin_usd for q in quotes)
    return SimStats(
        n_lots=len(quotes),
        total_paddy_mt=round(total_paddy, 2),
        total_white_rice_mt=round(total_white, 2),
        avg_milling_yield_pct=round(avg_yield, 2),
        total_fob_usd=round(total_fob, 2),
        total_gross_margin_usd=round(total_margin, 2),
    )
