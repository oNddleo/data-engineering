"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from hllpp.io_jsonl import (
    dump_sketches,
    load_sketches,
    sketch_from_dict,
    sketch_to_dict,
    stats_from_dict,
    stats_to_dict,
)
from hllpp.schema import SketchStats
from hllpp.sketch import add, new_sketch, stats


def test_sketch_round_trip_empty():
    s = new_sketch(precision=8)
    assert sketch_from_dict(sketch_to_dict(s)) == s


def test_sketch_round_trip_after_inserts():
    s = new_sketch(precision=10)
    for i in range(500):
        add(s, f"v_{i}")
    out = sketch_from_dict(sketch_to_dict(s))
    assert out.precision == s.precision
    assert out.registers == s.registers


def test_sketch_dump_load_many():
    sketches = []
    for seed in range(3):
        s = new_sketch(precision=8)
        for i in range(20):
            add(s, f"s{seed}_v_{i}")
        sketches.append(s)
    out = load_sketches(dump_sketches(sketches))
    assert out == sketches


def test_sketch_dump_newline_terminated():
    s = new_sketch(precision=4)
    text = dump_sketches([s])
    assert text.endswith("\n")


def test_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_sketches("[1, 2]\n")


def test_load_rejects_str_precision():
    bad = sketch_to_dict(new_sketch(precision=4))
    bad["precision"] = "four"
    with pytest.raises(TypeError, match="precision must be int"):
        sketch_from_dict(bad)


def test_stats_round_trip():
    s = new_sketch(precision=10)
    for i in range(100):
        add(s, f"v_{i}")
    summary = stats(s)
    assert stats_from_dict(stats_to_dict(summary)) == summary


def test_stats_round_trip_empty():
    s = new_sketch(precision=8)
    summary = stats(s)
    assert stats_from_dict(stats_to_dict(summary)) == summary


def test_stats_rejects_bool_n_zero():
    s = new_sketch(precision=8)
    bad = stats_to_dict(stats(s))
    bad["n_zero_registers"] = True
    with pytest.raises(TypeError, match="n_zero_registers must be int"):
        stats_from_dict(bad)


def test_sketch_serialization_is_compact():
    """base64-encoded register array is < 4× raw length."""
    import base64

    s = new_sketch(precision=14)
    text = dump_sketches([s])
    payload = text.splitlines()[0]
    # Raw bytes = m = 16384; base64 = ~22000 chars. JSON wrapper adds < 100 chars.
    assert len(payload) < 30_000

    # Verify the embedded base64 decodes back to 16384 bytes.
    import json

    parsed = json.loads(payload)
    decoded = base64.b64decode(parsed["registers_b64"])
    assert len(decoded) == 16_384


def test_sketch_preserves_register_byte_values():
    """Register values up to 255 round-trip correctly via base64."""
    s = new_sketch(precision=4)
    # Manually set max value (255 fits in one byte).
    s.registers[0] = 255
    s.registers[1] = 0
    s.registers[2] = 17
    out = sketch_from_dict(sketch_to_dict(s))
    assert out.registers[0] == 255
    assert out.registers[1] == 0
    assert out.registers[2] == 17


def test_stats_required_field_validates_m_consistency():
    """SketchStats validates m == 2^precision."""
    with pytest.raises(ValueError, match="m"):
        SketchStats(
            precision=4,
            m=99,
            n_zero_registers=0,
            max_register=0,
            estimated_cardinality=0,
            standard_error_pct=0.0,
        )
