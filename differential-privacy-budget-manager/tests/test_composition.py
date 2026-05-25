"""Tests for DP composition theorems."""

from __future__ import annotations

import pytest

from dpbudget.composition import (
    advanced_compose_epsilon,
    basic_compose_epsilon,
    moments_accountant_sigma,
    rdp_compose_epsilon,
)


class TestBasicComposition:
    def test_single_mechanism(self) -> None:
        assert basic_compose_epsilon([1.0]) == 1.0

    def test_sum_of_epsilons(self) -> None:
        assert abs(basic_compose_epsilon([0.5, 0.5, 1.0]) - 2.0) < 1e-9

    def test_empty(self) -> None:
        assert basic_compose_epsilon([]) == 0.0

    def test_homogeneous(self) -> None:
        result = basic_compose_epsilon([1.0] * 10)
        assert abs(result - 10.0) < 1e-9


class TestAdvancedComposition:
    def test_better_than_basic_for_many_queries(self) -> None:
        epsilons = [0.1] * 100
        basic = basic_compose_epsilon(epsilons)
        adv = advanced_compose_epsilon(epsilons, delta_prime=1e-5)
        # Advanced composition should give smaller ε for many small queries
        assert adv < basic

    def test_invalid_delta_zero(self) -> None:
        with pytest.raises(ValueError):
            advanced_compose_epsilon([1.0], delta_prime=0.0)

    def test_invalid_delta_one(self) -> None:
        with pytest.raises(ValueError):
            advanced_compose_epsilon([1.0], delta_prime=1.0)

    def test_empty(self) -> None:
        assert advanced_compose_epsilon([], delta_prime=1e-5) == 0.0

    def test_single_is_positive(self) -> None:
        assert advanced_compose_epsilon([1.0], 1e-5) > 0


class TestRDPComposition:
    def test_returns_positive(self) -> None:
        result = rdp_compose_epsilon([0.5, 0.5], alpha=2.0, delta=1e-5)
        assert result >= 0

    def test_more_queries_more_budget(self) -> None:
        r1 = rdp_compose_epsilon([0.5], alpha=2.0, delta=1e-5)
        r2 = rdp_compose_epsilon([0.5, 0.5], alpha=2.0, delta=1e-5)
        assert r2 >= r1

    def test_invalid_alpha(self) -> None:
        with pytest.raises(ValueError):
            rdp_compose_epsilon([1.0], alpha=1.0, delta=1e-5)


class TestMomentsAccountant:
    def test_sigma_positive(self) -> None:
        sigma = moments_accountant_sigma(1.0, 1e-5, 100)
        assert sigma > 0

    def test_more_queries_larger_sigma(self) -> None:
        s1 = moments_accountant_sigma(1.0, 1e-5, 10)
        s2 = moments_accountant_sigma(1.0, 1e-5, 1000)
        assert s2 > s1

    def test_tighter_epsilon_larger_sigma(self) -> None:
        s1 = moments_accountant_sigma(1.0, 1e-5, 100)
        s2 = moments_accountant_sigma(0.1, 1e-5, 100)
        assert s2 > s1

    def test_invalid_n_queries(self) -> None:
        with pytest.raises(ValueError):
            moments_accountant_sigma(1.0, 1e-5, 0)
