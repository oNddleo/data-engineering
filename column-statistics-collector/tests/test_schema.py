"""Schema validation: Bin / Histogram / TopKEntry / NumericStats / StringStats / ColumnProfile."""

from __future__ import annotations

import pytest

from colstats.schema import (
    Bin,
    ColumnKind,
    ColumnProfile,
    Histogram,
    HistogramKind,
    NumericStats,
    StringStats,
    TopKEntry,
)

# ---------- Bin --------------------------------------------------------------


def test_bin_basic():
    b = Bin(lower=0.0, upper=10.0, count=5)
    assert b.width == 10.0


def test_bin_rejects_negative_count():
    with pytest.raises(ValueError, match="count must be >= 0"):
        Bin(lower=0.0, upper=10.0, count=-1)


def test_bin_rejects_inverted_range():
    with pytest.raises(ValueError, match="upper.*lower"):
        Bin(lower=10.0, upper=5.0, count=0)


def test_bin_zero_width_ok():
    """Single-value bin (lower == upper)."""
    b = Bin(lower=5.0, upper=5.0, count=3)
    assert b.width == 0.0


# ---------- Histogram --------------------------------------------------------


def test_histogram_bin_counts_must_sum():
    bins = (Bin(0, 10, 5), Bin(10, 20, 5))
    Histogram(kind=HistogramKind.EQUI_WIDTH, bins=bins, total_count=10)


def test_histogram_rejects_bad_sum():
    bins = (Bin(0, 10, 5), Bin(10, 20, 5))
    with pytest.raises(ValueError, match="!= total_count"):
        Histogram(kind=HistogramKind.EQUI_WIDTH, bins=bins, total_count=42)


def test_histogram_empty_ok():
    h = Histogram(kind=HistogramKind.EQUI_WIDTH, bins=(), total_count=0)
    assert h.n_bins == 0


# ---------- TopKEntry --------------------------------------------------------


def test_topk_basic():
    t = TopKEntry(value="a", count=42)
    assert t.epsilon == 0


def test_topk_rejects_negative():
    with pytest.raises(ValueError, match="count"):
        TopKEntry(value="a", count=-1)
    with pytest.raises(ValueError, match="epsilon"):
        TopKEntry(value="a", count=0, epsilon=-1)


# ---------- NumericStats -----------------------------------------------------


def test_numeric_stats_rejects_negative_std():
    with pytest.raises(ValueError, match="std"):
        NumericStats(
            min=0,
            max=10,
            mean=5,
            std=-1,
            p25=2,
            p50=5,
            p75=7,
            p95=9,
            p99=10,
        )


# ---------- StringStats ------------------------------------------------------


def test_string_stats_rejects_inverted_lengths():
    with pytest.raises(ValueError, match="max_length"):
        StringStats(min_length=10, max_length=5, mean_length=7.5)


def test_string_stats_rejects_negative():
    with pytest.raises(ValueError, match="lengths"):
        StringStats(min_length=-1, max_length=5, mean_length=2.0)


# ---------- ColumnProfile ----------------------------------------------------


def test_column_profile_basic():
    p = ColumnProfile(
        name="amount",
        kind=ColumnKind.NUMERIC,
        n_rows=100,
        n_non_null=90,
        cardinality=87,
        cardinality_capped=False,
    )
    assert p.null_fraction == 0.1


def test_column_profile_zero_rows_zero_null_frac():
    p = ColumnProfile(
        name="col",
        kind=ColumnKind.STRING,
        n_rows=0,
        n_non_null=0,
        cardinality=0,
        cardinality_capped=False,
    )
    assert p.null_fraction == 0.0


def test_column_profile_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        ColumnProfile(
            name="",
            kind=ColumnKind.STRING,
            n_rows=0,
            n_non_null=0,
            cardinality=0,
            cardinality_capped=False,
        )


def test_column_profile_rejects_non_null_gt_rows():
    with pytest.raises(ValueError, match="n_non_null"):
        ColumnProfile(
            name="x",
            kind=ColumnKind.STRING,
            n_rows=5,
            n_non_null=10,
            cardinality=0,
            cardinality_capped=False,
        )


# ---------- Enum coverage ----------------------------------------------------


def test_column_kind_four_values():
    assert {k.value for k in ColumnKind} == {
        "NUMERIC",
        "STRING",
        "CATEGORICAL",
        "DATE",
    }


def test_histogram_kind_three_values():
    assert {k.value for k in HistogramKind} == {
        "EQUI_WIDTH",
        "EQUI_DEPTH",
        "MAXDIFF",
    }
