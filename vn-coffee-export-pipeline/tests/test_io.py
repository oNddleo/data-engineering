"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from vncoffee.io_jsonl import dump, load, lot_from_dict, lot_to_dict
from vncoffee.pricing import price_lot
from vncoffee.schema import CoffeeGrade, CoffeeSpecies, ContractType, ExportLot, Incoterm


def _sample() -> ExportLot:
    return ExportLot(
        lot_id="LOT-TEST",
        species=CoffeeSpecies.ROBUSTA,
        grade=CoffeeGrade.R1,
        contract=ContractType.DIFFERENTIAL,
        incoterm=Incoterm.FOB,
        volume_mt=50.0,
        futures_price_usd_mt=2800.0,
        differential_usd_mt=25.0,
    )


def test_roundtrip() -> None:
    p = price_lot(_sample())
    d = lot_to_dict(p)
    p2 = lot_from_dict(d)
    assert p2.fob_price_usd_mt == p.fob_price_usd_mt
    assert p2.total_fob_usd == p.total_fob_usd


def test_dump_load() -> None:
    p = price_lot(_sample())
    text = dump([p])
    loaded = load(text)
    assert len(loaded) == 1
    assert loaded[0].fob_price_usd_mt == p.fob_price_usd_mt


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
