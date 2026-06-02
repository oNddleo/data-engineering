"""JSONL codec round-trips."""

from __future__ import annotations

from datetime import date

import pytest

from vnfishery.io_jsonl import (
    dump_records,
    load_records,
    record_from_dict,
    record_to_dict,
)
from vnfishery.schema import ExportRecord, Form, Grade, Market, Species


def _sample() -> ExportRecord:
    return ExportRecord(
        shipment_id="S-001",
        exporter_tax_code="0312345678",
        species=Species.PANGASIUS,
        market=Market.US,
        grade=Grade.A,
        form=Form.FILLET,
        weight_kg=10_000,
        fob_price_usd_cents_per_kg=320,
        shipped_on=date(2026, 3, 15),
    )


def test_record_roundtrip() -> None:
    r = _sample()
    assert record_from_dict(record_to_dict(r)) == r


def test_dump_load_records() -> None:
    rs = [_sample()]
    assert load_records(dump_records(rs)) == rs


def test_load_blank_lines_ignored() -> None:
    text = dump_records([_sample()]) + "\n\n"
    assert len(load_records(text)) == 1


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_records("[1,2,3]\n")
