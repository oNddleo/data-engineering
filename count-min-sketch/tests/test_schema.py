"""Schema validation."""

from __future__ import annotations

import math

import pytest

from cms.schema import (
    CountMinSketch,
    HeavyHitter,
    SketchConfig,
    SketchStats,
)

# ---------- SketchConfig -----------------------------------------------------


def test_config_default_dimensions():
    c = SketchConfig()
    # ε=0.001, δ=0.001 → w=ceil(e/0.001), d=ceil(ln(1000))
    assert c.width == math.ceil(math.e / 0.001)  # 2719
    assert c.depth == math.ceil(math.log(1.0 / 0.001))  # 7


def test_config_tighter_error_narrows_width():
    c1 = SketchConfig(epsilon=0.01)
    c2 = SketchConfig(epsilon=0.001)
    assert c1.width < c2.width


def test_config_tighter_failure_increases_depth():
    c1 = SketchConfig(delta=0.01)
    c2 = SketchConfig(delta=0.001)
    assert c1.depth < c2.depth


def test_config_rejects_zero_epsilon():
    with pytest.raises(ValueError, match="epsilon"):
        SketchConfig(epsilon=0)


def test_config_rejects_negative_epsilon():
    with pytest.raises(ValueError, match="epsilon"):
        SketchConfig(epsilon=-0.1)


def test_config_rejects_one_epsilon():
    with pytest.raises(ValueError, match="epsilon"):
        SketchConfig(epsilon=1.0)


def test_config_rejects_zero_delta():
    with pytest.raises(ValueError, match="delta"):
        SketchConfig(delta=0)


# ---------- CountMinSketch ---------------------------------------------------


def test_sketch_default_zero_rows():
    s = CountMinSketch(config=SketchConfig())
    assert s.total_count == 0
    assert len(s.rows) == s.depth
    assert all(len(r) == s.width for r in s.rows)
    assert all(c == 0 for row in s.rows for c in row)


def test_sketch_with_explicit_rows():
    c = SketchConfig(epsilon=0.5, delta=0.5)  # tiny: w=6, d=1
    s = CountMinSketch(config=c, rows=[[0] * c.width])
    assert s.depth == 1


def test_sketch_rejects_wrong_row_count():
    """Passing rows with count != depth raises ValueError.

    (Empty list auto-fills, so we pass the wrong-size list explicitly.)
    """
    c = SketchConfig(epsilon=0.5, delta=0.5)
    # config gives depth=1; pass 2 rows to trigger validation.
    with pytest.raises(ValueError, match="rows count"):
        CountMinSketch(config=c, rows=[[0] * c.width, [0] * c.width])


def test_sketch_rejects_wrong_row_length():
    c = SketchConfig(epsilon=0.5, delta=0.5)
    with pytest.raises(ValueError, match="row length"):
        CountMinSketch(config=c, rows=[[0] * 99])


def test_sketch_rejects_negative_counter():
    c = SketchConfig(epsilon=0.5, delta=0.5)
    rows = [[-1] * c.width]
    with pytest.raises(ValueError, match="counters must be >= 0"):
        CountMinSketch(config=c, rows=rows)


def test_sketch_rejects_negative_total_count():
    with pytest.raises(ValueError, match="total_count"):
        CountMinSketch(config=SketchConfig(), total_count=-1)


def test_sketch_n_cells():
    s = CountMinSketch(config=SketchConfig())
    assert s.n_cells == s.depth * s.width


# ---------- HeavyHitter ------------------------------------------------------


def test_heavy_hitter_basic():
    h = HeavyHitter(value="x", estimated_count=42, fraction_of_total=0.42)
    assert h.value == "x"


def test_heavy_hitter_rejects_negative_count():
    with pytest.raises(ValueError, match="estimated_count"):
        HeavyHitter(value="x", estimated_count=-1, fraction_of_total=0.1)


def test_heavy_hitter_rejects_fraction_out_of_range():
    with pytest.raises(ValueError, match="fraction_of_total"):
        HeavyHitter(value="x", estimated_count=0, fraction_of_total=1.5)
    with pytest.raises(ValueError, match="fraction_of_total"):
        HeavyHitter(value="x", estimated_count=0, fraction_of_total=-0.1)


# ---------- SketchStats ------------------------------------------------------


def test_sketch_stats_basic():
    s = SketchStats(
        width=10,
        depth=3,
        n_cells=30,
        total_count=100,
        max_counter=42,
        epsilon=0.1,
        delta=0.05,
        standard_error_bound=10,
    )
    assert s.n_cells == 30
