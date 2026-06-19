"""Normalize sensor `(sensor_type, unit)` pairs to a single SI value.

For the POC the simulator already emits SI units (C / % / ug/m3 / mm/s),
so this is mostly a pass-through. Implemented as a UDF so future producers
that emit Fahrenheit or imperial units land in a consistent silver table.
"""

from __future__ import annotations

from pyspark.sql import functions as F
from pyspark.sql import types as T

CANONICAL_UNITS = {
    "temperature": "C",
    "humidity": "%",
    "pm25": "ug/m3",
    "vibration": "mm/s",
}


def _to_si(sensor_type: str | None, unit: str | None, value: float | None) -> float | None:
    if sensor_type is None or unit is None or value is None:
        return None
    canonical = CANONICAL_UNITS.get(sensor_type)
    if canonical is None or unit == canonical:
        return value
    # Future:
    # - sensor_type == "temperature" and unit == "F" → (value - 32) * 5/9
    # - sensor_type == "vibration" and unit == "in/s" → value * 25.4
    # For now anything unexpected gets returned as-is + flagged downstream.
    return value


to_si_value_udf = F.udf(_to_si, T.DoubleType())
