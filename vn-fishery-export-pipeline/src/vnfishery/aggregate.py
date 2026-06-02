"""Aggregation helpers — totals by species/market/exporter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from vnfishery.schema import ExportRecord, Market, Species

K = TypeVar("K")


@dataclass(frozen=True, slots=True)
class Aggregate:
    """Aggregated KPIs over a slice of export records."""

    n_shipments: int
    total_weight_kg: int
    total_fob_value_usd_cents: int

    @property
    def avg_price_usd_cents_per_kg(self) -> int:
        if self.total_weight_kg == 0:
            return 0
        return self.total_fob_value_usd_cents // self.total_weight_kg


def aggregate_by_species(
    records: Iterable[ExportRecord],
) -> dict[Species, Aggregate]:
    """Roll records up by species."""
    return _group_by(records, lambda r: r.species)


def aggregate_by_market(
    records: Iterable[ExportRecord],
) -> dict[Market, Aggregate]:
    return _group_by(records, lambda r: r.market)


def aggregate_by_species_market(
    records: Iterable[ExportRecord],
) -> dict[tuple[Species, Market], Aggregate]:
    return _group_by(records, lambda r: (r.species, r.market))


def aggregate_by_exporter(
    records: Iterable[ExportRecord],
) -> dict[str, Aggregate]:
    return _group_by(records, lambda r: r.exporter_tax_code)


def _group_by(
    records: Iterable[ExportRecord],
    key_fn: Callable[[ExportRecord], K],
) -> dict[K, Aggregate]:
    buckets: dict[K, list[int]] = {}
    for r in records:
        k = key_fn(r)
        if k not in buckets:
            buckets[k] = [0, 0, 0]  # n, weight, value
        agg = buckets[k]
        agg[0] += 1
        agg[1] += r.weight_kg
        agg[2] += r.fob_value_usd_cents
    return {
        k: Aggregate(
            n_shipments=v[0],
            total_weight_kg=v[1],
            total_fob_value_usd_cents=v[2],
        )
        for k, v in buckets.items()
    }


__all__ = [
    "Aggregate",
    "aggregate_by_exporter",
    "aggregate_by_market",
    "aggregate_by_species",
    "aggregate_by_species_market",
]
