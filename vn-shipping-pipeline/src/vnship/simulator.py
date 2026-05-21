"""Synthetic shipment generator for load-testing and benchmarking."""

from __future__ import annotations

import random
from dataclasses import dataclass

from vnship.pricing import calculate_fee
from vnship.schema import (
    Carrier,
    ServiceType,
    ShipmentRequest,
    ShipmentResult,
    ZoneType,
)

_ALL_CARRIERS = list(Carrier)
_SAME_DAY_CARRIERS = {Carrier.GHN, Carrier.GHTK, Carrier.JT}  # others lack SAME_DAY rate


@dataclass(frozen=True, slots=True)
class SimStats:
    n_shipments: int
    total_fee_vnd: int
    avg_fee_vnd: float
    carrier_counts: dict[str, int]
    cod_count: int


def generate(
    n: int = 100,
    seed: int = 0,
    max_weight_g: int = 20_000,
    cod_probability: float = 0.4,
    fragile_probability: float = 0.1,
) -> list[ShipmentResult]:
    """Generate *n* random shipments and price them."""
    if n <= 0:
        raise ValueError("n must be positive")
    rng = random.Random(seed)
    results: list[ShipmentResult] = []

    for _ in range(n):
        carrier = rng.choice(_ALL_CARRIERS)
        zone = rng.choice(list(ZoneType))
        # SAME_DAY only inner city + limited carriers
        if zone == ZoneType.INTER_PROVINCE:
            service = rng.choice([ServiceType.STANDARD, ServiceType.EXPRESS])
        elif carrier in _SAME_DAY_CARRIERS:
            service = rng.choice(list(ServiceType))
        else:
            service = rng.choice([ServiceType.STANDARD, ServiceType.EXPRESS])

        weight_g = rng.randint(100, max_weight_g)
        declared = rng.randint(50_000, 10_000_000)
        cod = rng.randint(50_000, declared) if rng.random() < cod_probability else 0
        fragile = rng.random() < fragile_probability

        req = ShipmentRequest(
            carrier=carrier,
            service=service,
            zone=zone,
            weight_g=weight_g,
            declared_value_vnd=declared,
            cod_amount_vnd=cod,
            is_fragile=fragile,
        )
        results.append(calculate_fee(req))

    return results


def summarise(results: list[ShipmentResult]) -> SimStats:
    """Aggregate a batch of results into summary stats."""
    if not results:
        return SimStats(
            n_shipments=0,
            total_fee_vnd=0,
            avg_fee_vnd=0.0,
            carrier_counts={},
            cod_count=0,
        )
    total = sum(r.total_fee_vnd for r in results)
    carrier_counts: dict[str, int] = {}
    cod_count = 0
    for r in results:
        key = r.request.carrier.value
        carrier_counts[key] = carrier_counts.get(key, 0) + 1
        if r.cod_fee_vnd > 0:
            cod_count += 1
    return SimStats(
        n_shipments=len(results),
        total_fee_vnd=total,
        avg_fee_vnd=total / len(results),
        carrier_counts=carrier_counts,
        cod_count=cod_count,
    )
