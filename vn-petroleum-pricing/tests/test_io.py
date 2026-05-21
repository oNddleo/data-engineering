"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from vnpetro.io_jsonl import dump, load
from vnpetro.pricing import calculate_retail_price
from vnpetro.schema import FuelType, PriceInput, PriceRegion


def test_dump_load() -> None:
    inp = PriceInput(
        fuel_type=FuelType.RON95_III,
        region=PriceRegion.SOUTH,
        cif_price_usd_per_barrel=85.0,
        usd_to_vnd=24_500.0,
    )
    b = calculate_retail_price(inp)
    text = dump([b])
    loaded = load(text)
    assert len(loaded) == 1
    assert loaded[0].fuel_type == b.fuel_type
    assert loaded[0].retail_price_vnd_per_litre == b.retail_price_vnd_per_litre


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
