"""Drift scoring (PSI + KS) with bin-aligned profiles."""

from __future__ import annotations

from dataclasses import replace

import pytest

from colstats.drift import ks, psi, psi_band
from colstats.histogram import reproject
from colstats.profile import collect_profile
from colstats.schema import ColumnKind


def _profile(values: list[float], name: str = "x") -> object:
    return collect_profile(
        name,
        [str(v) for v in values],
        kind=ColumnKind.NUMERIC,
    )


def test_psi_identical_profile_zero():
    """A profile compared to itself should score 0 PSI."""
    p = _profile([float(i) for i in range(100)])
    score = psi(p, p)
    assert abs(score) < 1e-9


def test_psi_shifted_profile_detects_drift():
    """A noticeably shifted distribution scores > 0.25 PSI (significant)."""
    baseline = collect_profile(
        "x",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
    )
    assert baseline.histogram is not None
    drifted_values = [float(i + 200) for i in range(100)]
    drift_hist = reproject(drifted_values, baseline.histogram)
    compared = replace(
        baseline,
        n_rows=len(drifted_values),
        n_non_null=len(drifted_values),
        histogram=drift_hist,
    )
    score = psi(baseline, compared)
    assert psi_band(score) == "significant"


def test_psi_modest_shift():
    """A modest shift (30% of range) falls in 'minor' or 'significant'."""
    baseline = collect_profile(
        "x",
        [str(float(i)) for i in range(1000)],
        kind=ColumnKind.NUMERIC,
    )
    assert baseline.histogram is not None
    compared_values = [float(i + 300) for i in range(1000)]
    compared_hist = reproject(compared_values, baseline.histogram)
    compared = replace(
        baseline,
        n_rows=len(compared_values),
        n_non_null=len(compared_values),
        histogram=compared_hist,
    )
    score = psi(baseline, compared)
    band = psi_band(score)
    assert band in ("minor", "significant")


def test_psi_rejects_missing_histograms():
    p1 = collect_profile("a", ["alpha", "beta"], kind=ColumnKind.STRING)
    p2 = collect_profile("a", ["gamma", "delta"], kind=ColumnKind.STRING)
    with pytest.raises(ValueError, match="histograms"):
        psi(p1, p2)


def test_psi_rejects_mismatched_bin_count():
    p1 = collect_profile(
        "a",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
        histogram_bins=5,
    )
    p2 = collect_profile(
        "a",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
        histogram_bins=10,
    )
    with pytest.raises(ValueError, match="bin count mismatch"):
        psi(p1, p2)


def test_psi_handles_zero_total():
    """A reprojected histogram with 0 counts → PSI 0 (no information)."""
    p1 = collect_profile(
        "a",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
    )
    assert p1.histogram is not None
    # Build a compared profile with the same histogram shape but zero counts.
    empty_hist = reproject([], p1.histogram)
    p2 = replace(p1, n_rows=0, n_non_null=0, histogram=empty_hist)
    score = psi(p1, p2)
    assert score == 0.0


# ---------- KS ---------------------------------------------------------------


def test_ks_identical_profile_zero():
    p = _profile([float(i) for i in range(100)])
    assert ks(p, p) == 0.0


def test_ks_in_unit_interval():
    """KS is always in [0, 1]."""
    baseline = collect_profile(
        "x",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
    )
    assert baseline.histogram is not None
    drifted_values = [float(i + 1000) for i in range(100)]
    drift_hist = reproject(drifted_values, baseline.histogram)
    compared = replace(
        baseline,
        n_rows=len(drifted_values),
        n_non_null=len(drifted_values),
        histogram=drift_hist,
    )
    score = ks(baseline, compared)
    assert 0.0 <= score <= 1.0


def test_ks_shifted_distribution_nonzero():
    """A drift causes non-zero KS."""
    baseline = collect_profile(
        "x",
        [str(float(i)) for i in range(100)],
        kind=ColumnKind.NUMERIC,
    )
    assert baseline.histogram is not None
    drifted_values = [float(i + 200) for i in range(100)]
    drift_hist = reproject(drifted_values, baseline.histogram)
    compared = replace(
        baseline,
        n_rows=len(drifted_values),
        n_non_null=len(drifted_values),
        histogram=drift_hist,
    )
    assert ks(baseline, compared) > 0.0


# ---------- psi_band thresholds ----------------------------------------------


def test_psi_band_thresholds():
    assert psi_band(0.0) == "stable"
    assert psi_band(0.05) == "stable"
    assert psi_band(0.099) == "stable"
    assert psi_band(0.1) == "minor"
    assert psi_band(0.2) == "minor"
    assert psi_band(0.249) == "minor"
    assert psi_band(0.25) == "significant"
    assert psi_band(1.0) == "significant"
