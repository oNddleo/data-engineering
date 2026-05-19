"""Schema invariants: Centroid, TDigest, BuildableTDigest."""

from __future__ import annotations

import math

import pytest

from tdigest.schema import BuildableTDigest, Centroid, TDigest

# ---------- Centroid --------------------------------------------------------


def test_centroid_basic() -> None:
    c = Centroid(mean=1.5, weight=10.0)
    assert c.mean == 1.5
    assert c.weight == 10.0


def test_centroid_zero_weight_allowed() -> None:
    """Zero weight is valid (degenerate centroid)."""
    c = Centroid(mean=0.0, weight=0.0)
    assert c.weight == 0.0


def test_centroid_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="weight"):
        Centroid(mean=1.0, weight=-0.1)


def test_centroid_rejects_nan_mean() -> None:
    with pytest.raises(ValueError, match="NaN"):
        Centroid(mean=float("nan"), weight=1.0)


def test_centroid_allows_infinite_mean() -> None:
    """Infinity is a valid (degenerate) centroid mean."""
    c = Centroid(mean=math.inf, weight=1.0)
    assert math.isinf(c.mean)


# ---------- TDigest ---------------------------------------------------------


def test_tdigest_basic() -> None:
    centroids = (Centroid(1.0, 5.0), Centroid(2.0, 3.0))
    td = TDigest(
        compression=100.0,
        centroids=centroids,
        total_weight=8.0,
        min_value=0.5,
        max_value=2.5,
    )
    assert td.n_centroids == 2


def test_tdigest_rejects_unsorted_centroids() -> None:
    with pytest.raises(ValueError, match="not sorted"):
        TDigest(
            compression=100.0,
            centroids=(Centroid(2.0, 1.0), Centroid(1.0, 1.0)),
            total_weight=2.0,
            min_value=1.0,
            max_value=2.0,
        )


def test_tdigest_rejects_weight_mismatch() -> None:
    with pytest.raises(ValueError, match="weights sum"):
        TDigest(
            compression=100.0,
            centroids=(Centroid(1.0, 1.0), Centroid(2.0, 1.0)),
            total_weight=99.0,
            min_value=0.5,
            max_value=2.5,
        )


def test_tdigest_rejects_low_compression() -> None:
    with pytest.raises(ValueError, match="compression"):
        TDigest(
            compression=0.5,
            centroids=(),
            total_weight=0.0,
            min_value=0.0,
            max_value=0.0,
        )


def test_tdigest_empty_is_valid() -> None:
    td = TDigest(
        compression=100.0,
        centroids=(),
        total_weight=0.0,
        min_value=0.0,
        max_value=0.0,
    )
    assert td.n_centroids == 0


# ---------- BuildableTDigest ------------------------------------------------


def test_buildable_basic() -> None:
    td = BuildableTDigest(compression=100.0, buffer_size=500)
    assert td.compression == 100.0
    assert td.total_weight == 0.0


def test_buildable_rejects_low_compression() -> None:
    with pytest.raises(ValueError, match="compression"):
        BuildableTDigest(compression=0.5, buffer_size=10)


def test_buildable_rejects_zero_buffer() -> None:
    with pytest.raises(ValueError, match="buffer_size"):
        BuildableTDigest(compression=100.0, buffer_size=0)
