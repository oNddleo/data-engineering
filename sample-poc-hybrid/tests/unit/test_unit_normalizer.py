"""Unit tests for `lib.unit_normalizer._to_si`.

Pure-Python tests — no Spark required.
"""

from __future__ import annotations

import pytest

from lib.unit_normalizer import _to_si


@pytest.mark.parametrize(
    "sensor_type, unit, value, expected",
    [
        ("temperature", "C", 27.5, 27.5),
        ("humidity",    "%", 60.0, 60.0),
        ("pm25",        "ug/m3", 55.0, 55.0),
        ("vibration",   "mm/s", 1.2, 1.2),
        ("temperature", "C", 0.0, 0.0),
    ],
)
def test_to_si_passthrough_si_units(sensor_type, unit, value, expected):
    assert _to_si(sensor_type, unit, value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "sensor_type, unit, value",
    [
        (None,          "C",     27.0),
        ("temperature", None,    27.0),
        ("temperature", "C",     None),
    ],
)
def test_to_si_returns_none_for_missing_inputs(sensor_type, unit, value):
    assert _to_si(sensor_type, unit, value) is None


def test_to_si_unknown_sensor_returns_value_unchanged():
    """Future producers may emit sensor_types we haven't mapped — pass through
    rather than silently nulling so the row still lands in silver."""
    assert _to_si("co2", "ppm", 410.0) == 410.0
