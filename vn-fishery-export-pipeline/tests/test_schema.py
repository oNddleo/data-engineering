"""ExportRecord validation."""

from __future__ import annotations

from datetime import date

import pytest

from vnfishery.schema import ExportRecord, Form, Grade, Market, Species


def _record(**overrides: object) -> ExportRecord:
    fields: dict[str, object] = {
        "shipment_id": "S-001",
        "exporter_tax_code": "0312345678",
        "species": Species.PANGASIUS,
        "market": Market.US,
        "grade": Grade.A,
        "form": Form.FILLET,
        "weight_kg": 10_000,
        "fob_price_usd_cents_per_kg": 320,
        "shipped_on": date(2026, 3, 15),
    }
    fields.update(overrides)
    return ExportRecord(**fields)  # type: ignore[arg-type]


def test_basic_construction() -> None:
    r = _record()
    assert r.species == Species.PANGASIUS
    assert r.fob_value_usd_cents == 3_200_000  # 10_000 * 320


def test_rejects_empty_shipment_id() -> None:
    with pytest.raises(ValueError):
        _record(shipment_id="")


def test_rejects_empty_tax_code() -> None:
    with pytest.raises(ValueError):
        _record(exporter_tax_code="")


def test_rejects_zero_weight() -> None:
    with pytest.raises(ValueError):
        _record(weight_kg=0)


def test_rejects_negative_price() -> None:
    with pytest.raises(ValueError):
        _record(fob_price_usd_cents_per_kg=-1)


def test_zero_price_allowed() -> None:
    """Free-of-charge samples are a real edge case (gifts, demos)."""
    r = _record(fob_price_usd_cents_per_kg=0)
    assert r.fob_value_usd_cents == 0


def test_frozen() -> None:
    r = _record()
    with pytest.raises(Exception):
        r.weight_kg = 1  # type: ignore[misc]
