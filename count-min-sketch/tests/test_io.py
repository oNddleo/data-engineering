"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from cms.io_jsonl import (
    dump_heavy_hitters,
    dump_sketches,
    heavy_hitter_from_dict,
    heavy_hitter_to_dict,
    load_heavy_hitters,
    load_sketches,
    sketch_from_dict,
    sketch_to_dict,
    stats_from_dict,
    stats_to_dict,
)
from cms.schema import HeavyHitter, SketchConfig
from cms.sketch import new_sketch, stats, update


def test_sketch_round_trip_empty():
    s = new_sketch(SketchConfig(epsilon=0.5, delta=0.5))
    assert sketch_from_dict(sketch_to_dict(s)) == s


def test_sketch_round_trip_after_inserts():
    s = new_sketch()
    for i in range(500):
        s = update(s, f"v_{i}")
    out = sketch_from_dict(sketch_to_dict(s))
    assert out.total_count == s.total_count
    assert out.rows == s.rows


def test_sketch_round_trip_preserves_max_count():
    """A counter near MAX_COUNT survives base64 roundtrip."""
    c = SketchConfig(epsilon=0.5, delta=0.5)  # tiny: w=6, d=1
    s = new_sketch(c)
    s = update(s, "x", count=4_000_000_000)
    out = sketch_from_dict(sketch_to_dict(s))
    assert out.rows == s.rows


def test_sketch_dump_load_many():
    sketches = []
    for seed in range(3):
        s = new_sketch()
        for i in range(20):
            s = update(s, f"s{seed}_v_{i}")
        sketches.append(s)
    out = load_sketches(dump_sketches(sketches))
    assert out == sketches


def test_sketch_dump_newline_terminated():
    s = new_sketch()
    text = dump_sketches([s])
    assert text.endswith("\n")


def test_load_rejects_non_object():
    with pytest.raises(TypeError, match="expected JSON object"):
        load_sketches("[1, 2]\n")


def test_load_rejects_wrong_row_count():
    s = new_sketch()
    bad = sketch_to_dict(s)
    bad["rows_b64"] = bad["rows_b64"][:-1]  # drop one row
    with pytest.raises(ValueError, match="row count"):
        sketch_from_dict(bad)


def test_load_rejects_str_total_count():
    s = new_sketch()
    bad = sketch_to_dict(s)
    bad["total_count"] = "0"
    with pytest.raises(TypeError, match="total_count must be int"):
        sketch_from_dict(bad)


def test_heavy_hitter_round_trip():
    h = HeavyHitter(value="x", estimated_count=42, fraction_of_total=0.42)
    assert heavy_hitter_from_dict(heavy_hitter_to_dict(h)) == h


def test_heavy_hitter_dump_load_many():
    hh = [
        HeavyHitter(value=f"v_{i}", estimated_count=100 - i, fraction_of_total=(100 - i) / 500)
        for i in range(5)
    ]
    assert load_heavy_hitters(dump_heavy_hitters(hh)) == hh


def test_stats_round_trip():
    s = new_sketch()
    for i in range(50):
        s = update(s, f"v_{i}")
    summary = stats(s)
    assert stats_from_dict(stats_to_dict(summary)) == summary


def test_sketch_payload_is_compact():
    """Base64-encoded rows fit within reasonable size budgets."""
    s = new_sketch(SketchConfig(epsilon=0.001, delta=0.001))  # ~74 KB raw
    text = dump_sketches([s])
    line = text.splitlines()[0]
    # Each counter is 4 bytes; 7 × 2719 = 19033 cells × 4 = 76132 bytes raw,
    # base64-encoded ≈ 102 KB. Plus JSON wrapper.
    assert len(line) < 130_000
