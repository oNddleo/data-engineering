"""Test fixtures: meter-reading builders."""

from __future__ import annotations

from datetime import date
from typing import Any

from evn.schema import CustomerCategory, MeterReading


def make_reading(**overrides: Any) -> MeterReading:
    """Build a household meter reading with sensible defaults."""
    defaults: dict[str, Any] = {
        "customer_code": "PA00000000001",
        "category": CustomerCategory.HOUSEHOLD,
        "period_start": date(2025, 1, 1),
        "period_end": date(2025, 1, 28),
        "kwh_used": 150,
    }
    defaults.update(overrides)
    return MeterReading(**defaults)


__all__ = ["make_reading"]
