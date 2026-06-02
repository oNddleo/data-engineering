"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from evnmeter.schema import VN_TZ, ConsumptionInterval, Meter, MeterKind, Reading

DEFAULT_TS = datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)


def make_meter(**overrides: Any) -> Meter:
    defaults = {
        "meter_id": "M-0001",
        "customer_id": "C-0001",
        "kind": MeterKind.RESI_1P,
        "region_code": "HCMC",
        "installed_at": DEFAULT_TS - timedelta(days=365),
    }
    defaults.update(overrides)
    return Meter(**defaults)  # type: ignore[arg-type]


def make_reading(**overrides: Any) -> Reading:
    defaults = {
        "meter_id": "M-0001",
        "cumulative_kwh_x100": 100_000,
        "observed_at": DEFAULT_TS,
        "quality": "GOOD",
    }
    defaults.update(overrides)
    return Reading(**defaults)  # type: ignore[arg-type]


def make_interval(**overrides: Any) -> ConsumptionInterval:
    defaults = {
        "meter_id": "M-0001",
        "start_at": DEFAULT_TS,
        "end_at": DEFAULT_TS + timedelta(minutes=30),
        "kwh_x100": 50,
        "is_estimated": False,
    }
    defaults.update(overrides)
    return ConsumptionInterval(**defaults)  # type: ignore[arg-type]


__all__ = ["DEFAULT_TS", "make_interval", "make_meter", "make_reading"]
