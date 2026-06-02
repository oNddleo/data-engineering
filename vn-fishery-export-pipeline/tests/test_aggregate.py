"""Aggregation helpers."""

from __future__ import annotations

from datetime import date

from vnfishery.aggregate import (
    aggregate_by_exporter,
    aggregate_by_market,
    aggregate_by_species,
    aggregate_by_species_market,
)
from vnfishery.schema import ExportRecord, Form, Grade, Market, Species


def _r(
    species: Species,
    market: Market,
    weight: int,
    price: int,
    tax_code: str = "0312345678",
    shipment_id: str = "S",
) -> ExportRecord:
    return ExportRecord(
        shipment_id=shipment_id,
        exporter_tax_code=tax_code,
        species=species,
        market=market,
        grade=Grade.A,
        form=Form.FROZEN,
        weight_kg=weight,
        fob_price_usd_cents_per_kg=price,
        shipped_on=date(2026, 1, 1),
    )


def test_aggregate_by_species() -> None:
    records = [
        _r(Species.PANGASIUS, Market.US, 1000, 300, shipment_id="A"),
        _r(Species.PANGASIUS, Market.EU, 2000, 280, shipment_id="B"),
        _r(Species.WHITE_SHRIMP, Market.JP, 500, 1100, shipment_id="C"),
    ]
    agg = aggregate_by_species(records)
    assert agg[Species.PANGASIUS].n_shipments == 2
    assert agg[Species.PANGASIUS].total_weight_kg == 3000
    assert agg[Species.WHITE_SHRIMP].total_weight_kg == 500


def test_aggregate_by_market() -> None:
    records = [
        _r(Species.PANGASIUS, Market.US, 1000, 300, shipment_id="A"),
        _r(Species.WHITE_SHRIMP, Market.US, 500, 850, shipment_id="B"),
        _r(Species.PANGASIUS, Market.EU, 2000, 280, shipment_id="C"),
    ]
    agg = aggregate_by_market(records)
    assert agg[Market.US].n_shipments == 2
    assert agg[Market.EU].n_shipments == 1


def test_aggregate_by_species_market() -> None:
    records = [
        _r(Species.PANGASIUS, Market.US, 1000, 300, shipment_id="A"),
        _r(Species.PANGASIUS, Market.US, 2000, 320, shipment_id="B"),
        _r(Species.PANGASIUS, Market.EU, 1500, 280, shipment_id="C"),
    ]
    agg = aggregate_by_species_market(records)
    us_pang = agg[(Species.PANGASIUS, Market.US)]
    assert us_pang.n_shipments == 2
    assert us_pang.total_weight_kg == 3000
    # avg = (1000*300 + 2000*320) / 3000 = 940_000 / 3000 = 313 (int floor)
    assert us_pang.avg_price_usd_cents_per_kg == 313


def test_aggregate_by_exporter() -> None:
    records = [
        _r(Species.PANGASIUS, Market.US, 1000, 300, tax_code="X", shipment_id="A"),
        _r(Species.PANGASIUS, Market.US, 2000, 320, tax_code="X", shipment_id="B"),
        _r(Species.PANGASIUS, Market.US, 1000, 280, tax_code="Y", shipment_id="C"),
    ]
    agg = aggregate_by_exporter(records)
    assert agg["X"].n_shipments == 2
    assert agg["Y"].n_shipments == 1


def test_empty_input() -> None:
    assert aggregate_by_species([]) == {}


def test_avg_price_zero_weight_safe() -> None:
    """The avg-price property handles a fully-zero bucket gracefully."""
    from vnfishery.aggregate import Aggregate

    a = Aggregate(n_shipments=0, total_weight_kg=0, total_fob_value_usd_cents=0)
    assert a.avg_price_usd_cents_per_kg == 0
