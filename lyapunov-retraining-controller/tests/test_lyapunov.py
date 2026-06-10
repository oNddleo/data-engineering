"""The one-step expectation map and predicted V."""

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from lrc.distributions import Gaussian, fit_mle
from lrc.lyapunov import (
    effective_real_fraction,
    lyapunov_value,
    predicted_next_state,
    predicted_v,
)


def test_effective_fraction_rounds_to_whole_samples() -> None:
    assert effective_real_fraction(0.5, 10) == pytest.approx(0.5)
    assert effective_real_fraction(0.24, 10) == pytest.approx(0.2)
    assert effective_real_fraction(0.26, 10) == pytest.approx(0.3)


def test_effective_fraction_validates_inputs() -> None:
    with pytest.raises(ValueError):
        effective_real_fraction(1.5, 10)
    with pytest.raises(ValueError):
        effective_real_fraction(0.5, 1)


def test_pure_synthetic_shrinks_variance_by_mle_factor() -> None:
    model = Gaussian(0.0, 1.0)
    ref = Gaussian(0.0, 1.0)
    nxt = predicted_next_state(model, ref, alpha=0.0, n_fit=100)
    assert nxt.mu == pytest.approx(0.0)
    assert nxt.sigma2 == pytest.approx(0.99)  # (1 - 1/n) shrinkage


def test_pure_real_recenters_on_reference() -> None:
    model = Gaussian(5.0, 0.01)
    ref = Gaussian(0.0, 1.0)
    nxt = predicted_next_state(model, ref, alpha=1.0, n_fit=100)
    assert nxt.mu == pytest.approx(0.0)
    assert nxt.sigma2 == pytest.approx(0.99)


def test_mean_disagreement_adds_variance() -> None:
    model = Gaussian(4.0, 1.0)
    ref = Gaussian(0.0, 1.0)
    nxt = predicted_next_state(model, ref, alpha=0.5, n_fit=1000)
    # sigma_bar^2 = 1, cross term = 0.25 * 16 = 4
    assert nxt.sigma2 == pytest.approx(0.999 * 1.0 + 0.25 * 16.0)


def test_predicted_next_matches_simulated_expectation() -> None:
    """Certainty-equivalent map = empirical mean of many stochastic retrains."""
    rng = random.Random(123)
    model, ref, alpha, n_fit = Gaussian(1.5, 0.6), Gaussian(0.0, 1.0), 0.4, 50
    k = round(alpha * n_fit)
    mus, s2s = [], []
    for _ in range(4000):
        data = ref.sample(rng, k) + model.sample(rng, n_fit - k)
        fitted = fit_mle(data)
        mus.append(fitted.mu)
        s2s.append(fitted.sigma2)
    pred = predicted_next_state(model, ref, alpha, n_fit)
    assert sum(mus) / len(mus) == pytest.approx(pred.mu, abs=0.01)
    assert sum(s2s) / len(s2s) == pytest.approx(pred.sigma2, rel=0.02)


def test_predicted_v_zero_alpha_increases_v_for_collapsed_state() -> None:
    """Retraining on pure synthetic data cannot fix a drifted model."""
    model = Gaussian(2.0, 0.5)
    ref = Gaussian(0.0, 1.0)
    v_now = lyapunov_value(model, ref)
    assert predicted_v(model, ref, alpha=0.0, n_fit=200) > v_now * 0.99


def test_predicted_v_full_real_is_near_noise_floor() -> None:
    model = Gaussian(2.0, 0.5)
    ref = Gaussian(0.0, 1.0)
    assert predicted_v(model, ref, alpha=1.0, n_fit=200) < 0.01


@given(
    st.floats(min_value=-10, max_value=10),
    st.floats(min_value=0.01, max_value=10),
    st.floats(min_value=0, max_value=1),
)
def test_predicted_state_always_valid(mu_m: float, s2_m: float, alpha: float) -> None:
    ref = Gaussian(0.0, 1.0)
    nxt = predicted_next_state(Gaussian(mu_m, s2_m), ref, alpha, n_fit=100)
    assert nxt.sigma2 > 0.0
