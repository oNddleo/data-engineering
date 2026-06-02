"""Core t-digest operations: build, add, compress, quantile, cdf, merge, freeze."""

from __future__ import annotations

import math

import pytest

from tdigest.digest import (
    add,
    build,
    cdf,
    compress,
    freeze,
    merge,
    quantile,
    thaw,
)
from tdigest.simulator import (
    exact_quantile,
    gaussian_stream,
    lognormal_stream,
    uniform_stream,
)


def test_build_basic() -> None:
    td = build(compression=100.0)
    assert td.compression == 100.0
    assert td.total_weight == 0.0


def test_build_rejects_low_compression() -> None:
    with pytest.raises(ValueError, match="compression"):
        build(compression=0.5)


def test_add_increments_weight() -> None:
    td = build(compression=100.0)
    add(td, 1.0)
    add(td, 2.0)
    add(td, 3.0)
    assert td.total_weight == 3.0


def test_add_rejects_nan() -> None:
    td = build(compression=100.0)
    with pytest.raises(ValueError, match="NaN"):
        add(td, float("nan"))


def test_add_rejects_zero_weight() -> None:
    td = build(compression=100.0)
    with pytest.raises(ValueError, match="weight"):
        add(td, 1.0, weight=0.0)


def test_quantile_empty_digest_raises() -> None:
    td = build(compression=100.0)
    with pytest.raises(ValueError, match="empty"):
        quantile(td, 0.5)


def test_quantile_rejects_out_of_range() -> None:
    td = build(compression=100.0)
    add(td, 1.0)
    with pytest.raises(ValueError, match="q"):
        quantile(td, 1.5)


def test_quantile_zero_returns_min() -> None:
    td = build(compression=100.0)
    for v in (3.0, 1.0, 2.0):
        add(td, v)
    assert quantile(td, 0.0) == 1.0


def test_quantile_one_returns_max() -> None:
    td = build(compression=100.0)
    for v in (3.0, 1.0, 2.0):
        add(td, v)
    assert quantile(td, 1.0) == 3.0


def test_quantile_uniform_accurate() -> None:
    """100k uniform samples — p50 and p90 within 2% of exact."""
    vals = uniform_stream(100_000, seed=42)
    td = build(compression=200.0)
    for v in vals:
        add(td, v)
    snap = freeze(td)
    for q in (0.1, 0.25, 0.5, 0.75, 0.9):
        est = quantile(snap, q)
        exact = exact_quantile(vals, q)
        assert abs(est - exact) < 0.02, f"q={q}: est={est}, exact={exact}"


def test_quantile_gaussian_tails_accurate() -> None:
    """p99 and p999 within 5% on 100k gaussian samples at compression=200."""
    vals = gaussian_stream(100_000, seed=42)
    td = build(compression=200.0)
    for v in vals:
        add(td, v)
    snap = freeze(td)
    for q in (0.99, 0.999):
        est = quantile(snap, q)
        exact = exact_quantile(vals, q)
        rel = abs(est - exact) / max(abs(exact), 1e-6)
        assert rel < 0.05, f"q={q}: est={est}, exact={exact}, rel={rel}"


def test_quantile_lognormal_p99_accurate() -> None:
    """Heavy-tail (lognormal) p99 within 3% at compression=200."""
    vals = lognormal_stream(100_000, seed=42)
    td = build(compression=200.0)
    for v in vals:
        add(td, v)
    snap = freeze(td)
    est = quantile(snap, 0.99)
    exact = exact_quantile(vals, 0.99)
    rel = abs(est - exact) / abs(exact)
    assert rel < 0.03


# ---------- CDF -------------------------------------------------------------


def test_cdf_below_min_is_zero() -> None:
    td = build(compression=100.0)
    for v in (1.0, 2.0, 3.0):
        add(td, v)
    assert cdf(td, 0.5) == 0.0


def test_cdf_above_max_is_one() -> None:
    td = build(compression=100.0)
    for v in (1.0, 2.0, 3.0):
        add(td, v)
    assert cdf(td, 5.0) == 1.0


def test_cdf_quantile_roundtrip() -> None:
    """quantile(cdf(v)) ≈ v for values inside the support."""
    vals = uniform_stream(50_000, seed=1)
    td = build(compression=200.0)
    for v in vals:
        add(td, v)
    snap = freeze(td)
    for v in (0.1, 0.25, 0.5, 0.75, 0.9):
        q = cdf(snap, v)
        v_round = quantile(snap, q)
        assert abs(v - v_round) < 0.02


# ---------- Compression bound -----------------------------------------------


def test_compress_bounds_centroid_count() -> None:
    """Centroid count should stay below ~3 * compression."""
    td = build(compression=100.0)
    for i in range(50_000):
        add(td, float(i) / 50_000)
    compress(td)
    assert len(td._centroids) < 3 * 100


# ---------- Merge -----------------------------------------------------------


def test_merge_combines_streams() -> None:
    """Merging two digests must produce quantiles close to the union."""
    a_vals = gaussian_stream(50_000, mu=0.0, seed=1)
    b_vals = gaussian_stream(50_000, mu=2.0, seed=2)
    all_vals = a_vals + b_vals

    a = build(compression=200.0)
    for v in a_vals:
        add(a, v)
    b = build(compression=200.0)
    for v in b_vals:
        add(b, v)

    merged = merge(freeze(a), freeze(b))
    for q in (0.25, 0.5, 0.75, 0.9, 0.99):
        est = quantile(merged, q)
        exact = exact_quantile(all_vals, q)
        rel = abs(est - exact) / max(abs(exact), 0.01)
        assert rel < 0.06, f"q={q}: est={est}, exact={exact}, rel={rel}"


def test_merge_total_weight_sums() -> None:
    a = build()
    b = build()
    for v in range(100):
        add(a, float(v))
        add(b, float(v + 100))
    out = merge(freeze(a), freeze(b))
    assert out.total_weight == 200


# ---------- Freeze / thaw ---------------------------------------------------


def test_freeze_returns_snapshot() -> None:
    td = build(compression=100.0)
    for v in range(100):
        add(td, float(v))
    snap = freeze(td)
    assert snap.n_centroids > 0
    assert snap.total_weight == 100.0
    assert snap.min_value == 0.0
    assert snap.max_value == 99.0


def test_thaw_preserves_state() -> None:
    td = build(compression=100.0)
    for v in range(100):
        add(td, float(v))
    snap = freeze(td)
    rehydrated = thaw(snap)
    assert rehydrated.total_weight == snap.total_weight
    assert rehydrated.min_value == snap.min_value


def test_thaw_supports_continued_adds() -> None:
    """After thaw we can keep adding."""
    td = build(compression=100.0)
    for v in range(50):
        add(td, float(v))
    snap = freeze(td)
    td2 = thaw(snap)
    for v in range(50, 100):
        add(td2, float(v))
    snap2 = freeze(td2)
    assert snap2.total_weight == 100.0


# ---------- Edge cases ------------------------------------------------------


def test_single_value() -> None:
    td = build(compression=100.0)
    add(td, 42.0)
    assert quantile(td, 0.0) == 42.0
    assert quantile(td, 0.5) == 42.0
    assert quantile(td, 1.0) == 42.0


def test_all_identical_values() -> None:
    """A digest of N copies of the same value should report exactly that value."""
    td = build(compression=100.0)
    for _ in range(1_000):
        add(td, 7.0)
    snap = freeze(td)
    for q in (0.0, 0.1, 0.5, 0.9, 1.0):
        assert math.isclose(quantile(snap, q), 7.0)


def test_weighted_input() -> None:
    """Weights should affect the quantile."""
    td = build(compression=100.0)
    add(td, 1.0, weight=10.0)
    add(td, 2.0, weight=1.0)
    snap = freeze(td)
    # Total weight 11, 10/11 of it at 1.0 → p50 should be 1.0.
    assert math.isclose(quantile(snap, 0.4), 1.0)
