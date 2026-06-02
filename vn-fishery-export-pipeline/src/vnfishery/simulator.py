"""Deterministic synthetic export-record generator."""

from __future__ import annotations

import random
from datetime import date, timedelta

from vnfishery.benchmark import benchmark_usd_cents_per_kg
from vnfishery.schema import ExportRecord, Form, Grade, Market, Species

# Species → typical product forms
_FORMS_BY_SPECIES: dict[Species, tuple[Form, ...]] = {
    Species.PANGASIUS: (Form.FILLET, Form.FROZEN, Form.WHOLE),
    Species.WHITE_SHRIMP: (Form.PEELED, Form.FROZEN, Form.WHOLE),
    Species.BLACK_TIGER: (Form.PEELED, Form.FROZEN, Form.WHOLE),
    Species.SQUID: (Form.WHOLE, Form.FROZEN, Form.DRIED),
    Species.TUNA: (Form.FILLET, Form.FROZEN),
    Species.OTHER: (Form.FROZEN,),
}


def generate(n: int = 50, seed: int = 0) -> list[ExportRecord]:
    """Generate ``n`` synthetic export records.

    Prices are anchored to the benchmark table with ±20 % jitter, so
    most records are realistic and roughly 10 % of them fall under the
    dumping-threshold trigger.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    out: list[ExportRecord] = []
    base_date = date(2026, 1, 1)
    for i in range(n):
        species = rng.choice(list(Species))
        market = rng.choice(list(Market))
        grade = rng.choice([Grade.A, Grade.B, Grade.A, Grade.A])  # mostly A
        form = rng.choice(_FORMS_BY_SPECIES.get(species, (Form.FROZEN,)))
        bench = benchmark_usd_cents_per_kg(species, market, grade)
        if bench is None:
            # No benchmark — use a generic 500 cents/kg with wide jitter.
            unit_price = int(round(rng.uniform(200, 800)))
        else:
            unit_price = int(round(bench * rng.uniform(0.6, 1.1)))
        out.append(
            ExportRecord(
                shipment_id=f"S-{i:06d}",
                exporter_tax_code=f"03{rng.randint(10_000_000, 99_999_999)}",
                species=species,
                market=market,
                grade=grade,
                form=form,
                weight_kg=rng.randint(500, 50_000),
                fob_price_usd_cents_per_kg=unit_price,
                shipped_on=base_date + timedelta(days=rng.randint(0, 364)),
            )
        )
    return out


__all__ = ["generate"]
