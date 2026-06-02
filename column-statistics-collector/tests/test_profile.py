"""collect_profile end-to-end for each ColumnKind."""

from __future__ import annotations

from colstats.profile import collect_profile
from colstats.schema import ColumnKind, HistogramKind


def test_profile_numeric_basic():
    values = [str(v) for v in range(1, 101)]  # "1".."100"
    p = collect_profile("amount", values, kind=ColumnKind.NUMERIC)
    assert p.kind is ColumnKind.NUMERIC
    assert p.n_rows == 100
    assert p.n_non_null == 100
    assert p.numeric is not None
    assert p.numeric.min == 1.0
    assert p.numeric.max == 100.0
    assert p.histogram is not None
    assert p.histogram.n_bins == 10


def test_profile_numeric_with_nulls():
    """Empty string values count toward n_rows but not n_non_null."""
    values = ["1", "2", "", "3", ""]
    p = collect_profile("col", values, kind=ColumnKind.NUMERIC)
    assert p.n_rows == 5
    assert p.n_non_null == 3
    assert p.null_fraction == 0.4


def test_profile_numeric_drops_unparseable():
    """Non-numeric values are dropped during numeric stats."""
    values = ["1", "2", "hello", "3"]
    p = collect_profile("col", values, kind=ColumnKind.NUMERIC)
    assert p.numeric is not None
    # Only 3 numeric values parsed → min=1 max=3.
    assert p.numeric.min == 1.0
    assert p.numeric.max == 3.0


def test_profile_categorical():
    values = ["A"] * 50 + ["B"] * 30 + ["C"] * 20
    p = collect_profile("cat", values, kind=ColumnKind.CATEGORICAL)
    assert p.kind is ColumnKind.CATEGORICAL
    assert p.cardinality == 3
    assert len(p.top_k) == 3
    assert p.top_k[0].value == "A"
    assert p.top_k[0].count == 50


def test_profile_string():
    values = ["hello", "world", "foo", "bar"]
    p = collect_profile("name", values, kind=ColumnKind.STRING)
    assert p.kind is ColumnKind.STRING
    assert p.strings is not None
    assert p.strings.min_length == 3
    assert p.strings.max_length == 5


def test_profile_date_parsed_as_numeric():
    values = ["2026-01-01", "2026-06-15", "2026-12-31"]
    p = collect_profile("dob", values, kind=ColumnKind.DATE)
    assert p.kind is ColumnKind.DATE
    assert p.numeric is not None
    # Day offsets from epoch — should be monotone-ordered.
    assert p.numeric.min < p.numeric.max
    assert p.histogram is not None


def test_profile_empty():
    p = collect_profile("col", [], kind=ColumnKind.NUMERIC)
    assert p.n_rows == 0
    assert p.numeric is None
    assert p.histogram is None


def test_profile_histogram_kind_respected():
    values = [str(v) for v in range(1, 101)]
    p_ew = collect_profile(
        "c", values, kind=ColumnKind.NUMERIC, histogram_kind=HistogramKind.EQUI_WIDTH
    )
    p_ed = collect_profile(
        "c", values, kind=ColumnKind.NUMERIC, histogram_kind=HistogramKind.EQUI_DEPTH
    )
    assert p_ew.histogram is not None
    assert p_ed.histogram is not None
    assert p_ew.histogram.kind is HistogramKind.EQUI_WIDTH
    assert p_ed.histogram.kind is HistogramKind.EQUI_DEPTH


def test_profile_cardinality_capped():
    """Large distinct count → cardinality_capped = True."""
    values = [f"v_{i}" for i in range(2_000)]
    p = collect_profile("c", values, kind=ColumnKind.STRING, cardinality_cap=100)
    assert p.cardinality == 101
    assert p.cardinality_capped is True
