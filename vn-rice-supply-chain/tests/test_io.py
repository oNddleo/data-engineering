"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from vnrice.io_jsonl import dump, load, quote_from_dict, quote_to_dict
from vnrice.milling import mill
from vnrice.pricing import quote_export
from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety


def _sample_quote() -> object:
    lot = PaddyLot(
        lot_id="T001",
        variety=RiceVariety.JASMINE,
        grade=PaddyGrade.GRADE_1,
        weight_mt=100.0,
        moisture_pct=14.0,
        price_vnd_per_kg=7500.0,
    )
    return quote_export(mill(lot, MilledRiceSpec.PERCENT_5))


def test_roundtrip() -> None:
    q = _sample_quote()
    d = quote_to_dict(q)  # type: ignore[arg-type]
    q2 = quote_from_dict(d)
    assert q2.fob_price_usd_mt == q.fob_price_usd_mt  # type: ignore[union-attr]


def test_dump_load() -> None:
    q = _sample_quote()
    text = dump([q])  # type: ignore[list-item]
    loaded = load(text)
    assert len(loaded) == 1
    assert loaded[0].total_fob_usd > 0


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
