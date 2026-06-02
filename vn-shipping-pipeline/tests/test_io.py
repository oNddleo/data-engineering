"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from vnship.io_jsonl import dump, load, result_from_dict, result_to_dict
from vnship.pricing import calculate_fee
from vnship.schema import Carrier, ServiceType, ShipmentRequest, ZoneType


def _sample_result() -> object:
    req = ShipmentRequest(
        carrier=Carrier.GHN,
        service=ServiceType.STANDARD,
        zone=ZoneType.INNER_CITY,
        weight_g=500,
        declared_value_vnd=300_000,
        cod_amount_vnd=0,
        is_fragile=False,
    )
    return calculate_fee(req)


def test_roundtrip() -> None:
    r = _sample_result()
    assert result_from_dict(result_to_dict(r)) == r  # type: ignore[arg-type]


def test_dump_load() -> None:
    r = _sample_result()
    text = dump([r])  # type: ignore[list-item]
    loaded = load(text)
    assert loaded == [r]


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")


def test_dump_multiple() -> None:
    results = [
        calculate_fee(
            ShipmentRequest(
                carrier=Carrier.GHN,
                service=ServiceType.STANDARD,
                zone=ZoneType.INNER_CITY,
                weight_g=w,
                declared_value_vnd=100_000,
                cod_amount_vnd=0,
                is_fragile=False,
            )
        )
        for w in [300, 600, 1200]
    ]
    text = dump(results)
    loaded = load(text)
    assert loaded == results
