"""Three histogram constructors + reproject."""

from __future__ import annotations

import pytest

from colstats.histogram import equi_depth, equi_width, maxdiff, reproject

# ---------- equi_width -------------------------------------------------------


def test_equi_width_basic():
    h = equi_width([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], n_bins=5)
    assert h.n_bins == 5
    assert sum(b.count for b in h.bins) == 6
    # First bin lower = min, last bin upper = max.
    assert h.bins[0].lower == 0.0
    assert h.bins[-1].upper == 5.0


def test_equi_width_uniform_distribution():
    """Uniform [0, 100] in 10 bins → roughly equal counts."""
    values = [float(i) for i in range(100)]
    h = equi_width(values, n_bins=10)
    counts = [b.count for b in h.bins]
    assert all(8 <= c <= 12 for c in counts)


def test_equi_width_degenerate_all_equal():
    """All identical values → one collapsed bin holding everything."""
    h = equi_width([5.0] * 10)
    assert sum(b.count for b in h.bins) == 10


def test_equi_width_empty():
    h = equi_width([], n_bins=5)
    assert h.n_bins == 0


def test_equi_width_rejects_zero_bins():
    with pytest.raises(ValueError, match="n_bins"):
        equi_width([1.0, 2.0], n_bins=0)


# ---------- equi_depth -------------------------------------------------------


def test_equi_depth_balanced():
    """Equal-depth bins should hold approximately N/B values each."""
    values = [float(i) for i in range(100)]
    h = equi_depth(values, n_bins=10)
    counts = [b.count for b in h.bins]
    assert all(8 <= c <= 12 for c in counts)


def test_equi_depth_total_count_preserved():
    h = equi_depth([float(i) for i in range(99)], n_bins=10)
    assert sum(b.count for b in h.bins) == 99


def test_equi_depth_empty():
    h = equi_depth([], n_bins=5)
    assert h.n_bins == 0


# ---------- maxdiff ----------------------------------------------------------


def test_maxdiff_few_distinct_one_bin_per_value():
    """When distinct count <= n_bins, one bin per distinct value."""
    h = maxdiff([1.0, 1.0, 2.0, 2.0, 3.0], n_bins=10)
    assert h.n_bins == 3  # 3 distinct values
    assert sum(b.count for b in h.bins) == 5


def test_maxdiff_cuts_at_largest_gaps():
    """A bimodal distribution should have a bin boundary at the gap."""
    values = [1.0, 1.1, 1.2, 100.0, 100.1, 100.2]
    h = maxdiff(values, n_bins=2)
    # The first bin holds the cluster around 1, the second holds the cluster around 100.
    assert h.bins[0].upper < 50.0
    assert h.bins[1].lower > 50.0


def test_maxdiff_total_count_preserved():
    values = [float(i) for i in range(50)]
    h = maxdiff(values, n_bins=10)
    assert sum(b.count for b in h.bins) == 50


def test_maxdiff_empty():
    h = maxdiff([], n_bins=10)
    assert h.n_bins == 0


# ---------- reproject --------------------------------------------------------


def test_reproject_preserves_template_edges():
    """Reprojection preserves the template's bin edges."""
    template = equi_width([float(i) for i in range(100)], n_bins=5)
    new_values = [float(i) for i in range(200)]
    out = reproject(new_values, template)
    # Edges match
    for a, b in zip(template.bins, out.bins, strict=True):
        assert a.lower == b.lower
        assert a.upper == b.upper
    # Total count = number of new values
    assert sum(b.count for b in out.bins) == 200


def test_reproject_clamps_out_of_range():
    """Values below first edge → bin 0; above last edge → last bin."""
    template = equi_width([10.0, 20.0], n_bins=2)
    out = reproject([-100.0, 100.0], template)
    assert sum(b.count for b in out.bins) == 2
    assert out.bins[0].count >= 1
    assert out.bins[-1].count >= 1


def test_reproject_empty_template():
    template = equi_width([], n_bins=5)
    out = reproject([1.0, 2.0], template)
    assert out.n_bins == 0
