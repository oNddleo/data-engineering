"""Tests for Laplace and Gaussian noise mechanisms."""

from __future__ import annotations

import math
import random
import statistics

import pytest

from dpbudget.mechanisms import (
    apply_gaussian,
    apply_laplace,
    default_sensitivity,
    gaussian_noise,
    gaussian_std,
    laplace_noise,
    laplace_std,
)


class TestLaplaceNoise:
    def test_returns_float(self) -> None:
        rng = random.Random(0)
        n = laplace_noise(1.0, 1.0, rng)
        assert isinstance(n, float)

    def test_invalid_epsilon_zero(self) -> None:
        with pytest.raises(ValueError, match="epsilon"):
            laplace_noise(1.0, 0.0)

    def test_invalid_epsilon_negative(self) -> None:
        with pytest.raises(ValueError, match="epsilon"):
            laplace_noise(1.0, -1.0)

    def test_invalid_sensitivity(self) -> None:
        with pytest.raises(ValueError, match="sensitivity"):
            laplace_noise(0.0, 1.0)

    def test_zero_mean_empirically(self) -> None:
        rng = random.Random(7)
        samples = [laplace_noise(1.0, 1.0, rng) for _ in range(5000)]
        assert abs(statistics.mean(samples)) < 0.1

    def test_scale_proportional_to_sensitivity(self) -> None:
        rng1 = random.Random(1)
        rng2 = random.Random(1)
        s1 = statistics.stdev([laplace_noise(1.0, 1.0, rng1) for _ in range(3000)])
        s2 = statistics.stdev([laplace_noise(2.0, 1.0, rng2) for _ in range(3000)])
        # std(Lap(0,2)) ≈ 2 * std(Lap(0,1))
        assert 1.5 < s2 / s1 < 2.5

    def test_scale_inversely_proportional_to_epsilon(self) -> None:
        rng1 = random.Random(2)
        rng2 = random.Random(2)
        s1 = statistics.stdev([laplace_noise(1.0, 1.0, rng1) for _ in range(3000)])
        s2 = statistics.stdev([laplace_noise(1.0, 2.0, rng2) for _ in range(3000)])
        assert s1 / s2 > 1.5

    def test_std_formula(self) -> None:
        std = laplace_std(1.0, 1.0)
        assert abs(std - math.sqrt(2)) < 1e-9

    def test_apply_laplace_returns_tuple(self) -> None:
        rng = random.Random(0)
        noisy, noise = apply_laplace(100.0, 1.0, 1.0, rng)
        assert abs(noisy - 100.0 - noise) < 1e-9


class TestGaussianNoise:
    def test_returns_float(self) -> None:
        rng = random.Random(0)
        n = gaussian_noise(1.0, 1.0, 1e-5, rng)
        assert isinstance(n, float)

    def test_invalid_epsilon(self) -> None:
        with pytest.raises(ValueError):
            gaussian_noise(1.0, 0.0, 1e-5)

    def test_invalid_delta_zero(self) -> None:
        with pytest.raises(ValueError):
            gaussian_noise(1.0, 1.0, 0.0)

    def test_invalid_delta_one(self) -> None:
        with pytest.raises(ValueError):
            gaussian_noise(1.0, 1.0, 1.0)

    def test_zero_mean_empirically(self) -> None:
        rng = random.Random(99)
        samples = [gaussian_noise(1.0, 1.0, 1e-5, rng) for _ in range(5000)]
        assert abs(statistics.mean(samples)) < 0.1

    def test_std_formula_matches_samples(self) -> None:
        rng = random.Random(3)
        expected = gaussian_std(1.0, 1.0, 1e-5)
        samples = [gaussian_noise(1.0, 1.0, 1e-5, rng) for _ in range(5000)]
        actual = statistics.stdev(samples)
        # within 10 %
        assert abs(actual - expected) / expected < 0.10

    def test_apply_gaussian_returns_tuple(self) -> None:
        rng = random.Random(0)
        noisy, noise = apply_gaussian(100.0, 1.0, 1.0, 1e-5, rng)
        assert abs(noisy - 100.0 - noise) < 1e-9


class TestDefaultSensitivity:
    def test_count_is_one(self) -> None:
        assert default_sensitivity("count") == 1.0

    def test_histogram_is_one(self) -> None:
        assert default_sensitivity("histogram") == 1.0

    def test_sum_uses_range(self) -> None:
        assert default_sensitivity("sum", 100.0) == 100.0

    def test_sum_defaults_one(self) -> None:
        assert default_sensitivity("sum") == 1.0

    def test_unknown_defaults_one(self) -> None:
        assert default_sensitivity("custom_query") == 1.0
