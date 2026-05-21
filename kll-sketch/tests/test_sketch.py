"""Unit tests for KLL sketch."""

from __future__ import annotations

import random

import pytest

from kllsketch.sketch import KLLSketch


def _sketch_from(values: list[float], k: int = 200, seed: int = 42) -> KLLSketch:
    s = KLLSketch(k=k, seed=seed)
    for v in values:
        s.update(v)
    return s


class TestBasic:
    def test_n_tracks_insertions(self) -> None:
        s = KLLSketch()
        for i in range(100):
            s.update(float(i))
        assert s.n == 100

    def test_empty_quantile_raises(self) -> None:
        with pytest.raises(ValueError):
            KLLSketch().quantile(0.5)

    def test_invalid_phi_raises(self) -> None:
        s = _sketch_from([1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            s.quantile(0.0)
        with pytest.raises(ValueError):
            s.quantile(1.1)

    def test_k_too_small_raises(self) -> None:
        with pytest.raises(ValueError):
            KLLSketch(k=1)

    def test_single_item(self) -> None:
        s = _sketch_from([42.0])
        assert s.quantile(0.5) == pytest.approx(42.0)
        assert s.quantile(1.0) == pytest.approx(42.0)


class TestQuantileAccuracy:
    """Approximate quantile accuracy within 10% for large streams (KLL guarantee ~7% at k=200)."""

    def test_median_uniform(self) -> None:
        rng = random.Random(0)
        data = [rng.uniform(0, 1) for _ in range(50_000)]
        s = _sketch_from(data, k=200, seed=0)
        median = s.quantile(0.5)
        assert abs(median - 0.5) < 0.1

    def test_p90_uniform(self) -> None:
        rng = random.Random(1)
        data = [rng.uniform(0, 1) for _ in range(50_000)]
        s = _sketch_from(data, k=200, seed=1)
        p90 = s.quantile(0.9)
        assert abs(p90 - 0.9) < 0.1

    def test_p10_uniform(self) -> None:
        rng = random.Random(2)
        data = [rng.uniform(0, 1) for _ in range(50_000)]
        s = _sketch_from(data, k=200, seed=2)
        p10 = s.quantile(0.1)
        assert abs(p10 - 0.1) < 0.1

    def test_monotone_quantiles(self) -> None:
        rng = random.Random(3)
        data = [rng.gauss(0, 1) for _ in range(5_000)]
        s = _sketch_from(data, k=200, seed=3)
        q25 = s.quantile(0.25)
        q50 = s.quantile(0.5)
        q75 = s.quantile(0.75)
        assert q25 <= q50 <= q75


class TestMerge:
    def test_merge_n(self) -> None:
        s1 = _sketch_from(list(range(100)), seed=0)
        s2 = _sketch_from(list(range(100, 200)), seed=1)
        merged = s1.merge(s2)
        assert merged.n == 200

    def test_merge_median_close(self) -> None:
        rng = random.Random(7)
        data1 = [rng.uniform(0, 1) for _ in range(5_000)]
        data2 = [rng.uniform(0, 1) for _ in range(5_000)]
        s1 = _sketch_from(data1, k=200, seed=7)
        s2 = _sketch_from(data2, k=200, seed=8)
        merged = s1.merge(s2)
        assert abs(merged.quantile(0.5) - 0.5) < 0.1


class TestCDF:
    def test_cdf_min_is_positive(self) -> None:
        s = _sketch_from([1.0, 2.0, 3.0, 4.0, 5.0])
        assert s.cdf(1.0) > 0.0

    def test_cdf_max_is_one(self) -> None:
        s = _sketch_from([1.0, 2.0, 3.0])
        assert s.cdf(3.0) == pytest.approx(1.0)

    def test_cdf_monotone(self) -> None:
        s = _sketch_from(list(range(100)))
        assert s.cdf(10.0) <= s.cdf(50.0) <= s.cdf(90.0)

    def test_empty_cdf_is_zero(self) -> None:
        assert KLLSketch().cdf(0.0) == 0.0


class TestSize:
    def test_size_less_than_n(self) -> None:
        s = _sketch_from(list(range(10_000)), k=100)
        assert s.size() < 10_000
        assert s.size() > 0
