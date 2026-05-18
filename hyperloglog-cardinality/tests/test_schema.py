"""HLLSketch + SketchStats validation."""

from __future__ import annotations

import pytest

from hllpp.schema import (
    DEFAULT_PRECISION,
    MAX_PRECISION,
    MIN_PRECISION,
    HLLSketch,
    SketchStats,
)


def test_precision_constants():
    assert MIN_PRECISION == 4
    assert MAX_PRECISION == 16
    assert DEFAULT_PRECISION == 14


def test_sketch_default_register_array():
    """Empty register list auto-fills to 2^precision zeros."""
    s = HLLSketch(precision=10)
    assert s.m == 1024
    assert s.registers == [0] * 1024


def test_sketch_explicit_register_array():
    s = HLLSketch(precision=4, registers=[0] * 16)
    assert s.m == 16


def test_sketch_rejects_wrong_length_registers():
    with pytest.raises(ValueError, match="registers length"):
        HLLSketch(precision=4, registers=[0] * 10)


def test_sketch_rejects_low_precision():
    with pytest.raises(ValueError, match="precision must be in"):
        HLLSketch(precision=3)


def test_sketch_rejects_high_precision():
    with pytest.raises(ValueError, match="precision must be in"):
        HLLSketch(precision=17)


def test_sketch_rejects_negative_register():
    with pytest.raises(ValueError, match="registers must all be >= 0"):
        HLLSketch(precision=4, registers=[-1] + [0] * 15)


def test_sketch_n_zero_registers():
    s = HLLSketch(precision=4)
    assert s.n_zero_registers() == 16
    s.registers[0] = 5
    s.registers[3] = 2
    assert s.n_zero_registers() == 14


def test_sketch_stats_rejects_bad_m():
    with pytest.raises(ValueError, match="m"):
        SketchStats(
            precision=4,
            m=99,
            n_zero_registers=0,
            max_register=0,
            estimated_cardinality=0,
            standard_error_pct=0.0,
        )


def test_sketch_stats_rejects_negative_std_error():
    with pytest.raises(ValueError, match="standard_error_pct"):
        SketchStats(
            precision=4,
            m=16,
            n_zero_registers=0,
            max_register=0,
            estimated_cardinality=0,
            standard_error_pct=-1.0,
        )
