"""Seeded synthetic smart-meter telemetry.

Generates ``(meters, readings)`` pairs simulating a small EVN region.
Realism touches:

* Diurnal load curve — bias toward 18:00 – 22:00 peak.
* Per-meter base load (varies by household size).
* ``gap_fraction`` of readings are dropped to exercise the derive
  pass's gap-filling.
* ``out_of_order_fraction`` of readings are shuffled by one slot to
  exercise the resort step.
* ``rollover_fraction`` of meters start near ``METER_MAX_X100`` so
  the derive pass exercises the wrap branch.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from evnmeter.schema import METER_MAX_X100, VN_TZ, Meter, MeterKind, Reading

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
_REGIONS = ("HCMC", "HN", "DN", "CT", "HP", "NT", "BD", "BTH")


def _hourly_load_factor(hour: int) -> float:
    """0..1 factor multiplying base load by time of day."""
    # Smoothed bell-ish curve peaking ~19:00.
    return 0.30 + 0.70 * max(0.0, math.cos((hour - 19) * math.pi / 12) ** 2)


def generate(
    *,
    n_meters: int = 20,
    n_days: int = 7,
    interval_minutes: int = 30,
    gap_fraction: float = 0.02,
    out_of_order_fraction: float = 0.05,
    rollover_fraction: float = 0.0,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Meter], list[Reading]]:
    """Generate meters + 30-min cumulative readings over ``n_days``."""
    if n_meters < 1:
        raise ValueError("n_meters must be >= 1")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be > 0")
    for name, val in (
        ("gap_fraction", gap_fraction),
        ("out_of_order_fraction", out_of_order_fraction),
        ("rollover_fraction", rollover_fraction),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    meters: list[Meter] = []
    base_loads: dict[str, float] = {}
    starts: dict[str, int] = {}  # initial cumulative_kwh_x100 per meter
    for i in range(n_meters):
        kind = rng.choices(
            (MeterKind.RESI_1P, MeterKind.RESI_3P, MeterKind.COMM),
            weights=(0.80, 0.15, 0.05),
            k=1,
        )[0]
        meter_id = f"M-{i:06d}"
        meters.append(
            Meter(
                meter_id=meter_id,
                customer_id=f"C-{i:06d}",
                kind=kind,
                region_code=rng.choice(_REGIONS),
                installed_at=base - timedelta(days=365 * rng.randint(1, 5)),
            )
        )
        # Base load in kWh per 30-min interval — 0.2 kWh ≈ 400 W avg.
        base_loads[meter_id] = rng.uniform(0.10, 0.50)
        if rng.random() < rollover_fraction:
            # Start near rollover so the simulated stream wraps.
            starts[meter_id] = METER_MAX_X100 - rng.randint(100, 500)
        else:
            starts[meter_id] = rng.randint(10_000, 100_000_000)

    readings: list[Reading] = []
    n_intervals = n_days * (24 * 60 // interval_minutes)
    for meter in meters:
        cumulative = starts[meter.meter_id]
        for k in range(n_intervals):
            ts = base + timedelta(minutes=k * interval_minutes)
            hour = ts.hour
            factor = _hourly_load_factor(hour)
            kwh_this_interval = base_loads[meter.meter_id] * factor
            # × 100 for the integer cumulative; round to nearest.
            delta_x100 = int(kwh_this_interval * 100 + 0.5)
            cumulative = (cumulative + delta_x100) % (METER_MAX_X100 + 1)
            # Inject a missing reading occasionally.
            if rng.random() < gap_fraction:
                continue
            readings.append(
                Reading(
                    meter_id=meter.meter_id,
                    cumulative_kwh_x100=cumulative,
                    observed_at=ts,
                    quality="GOOD",
                )
            )

    # Shuffle ~``out_of_order_fraction`` adjacent pairs to simulate
    # NB-IoT packet reordering.
    for i in range(len(readings) - 1):
        if rng.random() < out_of_order_fraction:
            readings[i], readings[i + 1] = readings[i + 1], readings[i]

    return meters, readings


__all__ = ["generate"]
