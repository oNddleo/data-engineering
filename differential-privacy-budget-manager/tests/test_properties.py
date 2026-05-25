"""Hypothesis property tests for DP mechanisms and composition."""

from __future__ import annotations

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from dpbudget.composition import advanced_compose_epsilon, basic_compose_epsilon
from dpbudget.mechanisms import apply_laplace, laplace_std

_POS = st.floats(min_value=1e-3, max_value=10.0, allow_nan=False, allow_infinity=False)
_EPS = st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False)


class TestLaplaceProperties:
    @given(sensitivity=_POS, epsilon=_EPS)
    @settings(max_examples=100)
    def test_std_formula_positive(self, sensitivity: float, epsilon: float) -> None:
        std = laplace_std(sensitivity, epsilon)
        assert std > 0

    @given(sensitivity=_POS, epsilon=_EPS)
    @settings(max_examples=100)
    def test_std_scales_with_sensitivity(self, sensitivity: float, epsilon: float) -> None:
        s1 = laplace_std(sensitivity, epsilon)
        s2 = laplace_std(sensitivity * 2, epsilon)
        assert abs(s2 / s1 - 2.0) < 1e-9

    @given(sensitivity=_POS, epsilon=_EPS)
    @settings(max_examples=100)
    def test_std_inversely_scales_with_epsilon(self, sensitivity: float, epsilon: float) -> None:
        s1 = laplace_std(sensitivity, epsilon)
        s2 = laplace_std(sensitivity, epsilon * 2)
        assert abs(s1 / s2 - 2.0) < 1e-9

    @given(
        true_val=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        sensitivity=_POS,
        epsilon=_EPS,
    )
    @settings(max_examples=100)
    def test_noise_conserved_in_apply(
        self, true_val: float, sensitivity: float, epsilon: float
    ) -> None:
        rng = random.Random(0)
        noisy, noise = apply_laplace(true_val, sensitivity, epsilon, rng)
        assert abs(noisy - true_val - noise) < 1e-9


class TestCompositionProperties:
    @given(
        epsilons=st.lists(
            st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_basic_composition_monotone(self, epsilons: list[float]) -> None:
        """Adding more queries can only increase the total budget."""
        e1 = basic_compose_epsilon(epsilons)
        e2 = basic_compose_epsilon(epsilons + [0.1])
        assert e2 >= e1

    @given(
        n=st.integers(min_value=100, max_value=500),
        eps=st.floats(min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=40)
    def test_advanced_le_basic_for_many_small(self, n: int, eps: float) -> None:
        """For ≥100 small queries, advanced composition ε < basic."""
        # Advanced < basic when n > 2·ln(1/δ'), i.e. n > ~46 for δ'=1e-5
        epsilons = [eps] * n
        basic = basic_compose_epsilon(epsilons)
        adv = advanced_compose_epsilon(epsilons, delta_prime=1e-5)
        assert adv <= basic + 1e-9

    @given(
        epsilons=st.lists(
            st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=80)
    def test_advanced_composition_positive(self, epsilons: list[float]) -> None:
        result = advanced_compose_epsilon(epsilons, delta_prime=1e-5)
        assert result >= 0

    @given(
        a=st.lists(_EPS, min_size=1, max_size=5),
        b=st.lists(_EPS, min_size=1, max_size=5),
    )
    @settings(max_examples=60)
    def test_basic_composition_additive(self, a: list[float], b: list[float]) -> None:
        """Basic composition is additive: ε(A ∪ B) = ε(A) + ε(B)."""
        combined = basic_compose_epsilon(a + b)
        separate = basic_compose_epsilon(a) + basic_compose_epsilon(b)
        assert abs(combined - separate) < 1e-9
