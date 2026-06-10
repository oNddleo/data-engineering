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


def test_predicted_next_state_beta_zero_is_default() -> None:
    model, ref = Gaussian(1.0, 0.5), Gaussian(0.0, 1.0)
    assert predicted_next_state(model, ref, 0.5, 100) == predicted_next_state(
        model, ref, 0.5, 100, beta=0.0
    )


def test_predicted_next_state_beta_shrinks_toward_model() -> None:
    model, ref = Gaussian(2.0, 0.5), Gaussian(0.0, 1.0)
    plain = predicted_next_state(model, ref, 1.0, 100)
    damped = predicted_next_state(model, ref, 1.0, 100, beta=100.0)
    # With beta = n the update is halved: midway between plain and the old model.
    assert damped.mu == pytest.approx((plain.mu + model.mu) / 2)
    assert damped.sigma2 == pytest.approx((plain.sigma2 + model.sigma2) / 2)


def test_predicted_next_state_rejects_negative_beta() -> None:
    with pytest.raises(ValueError):
        predicted_next_state(Gaussian(0.0, 1.0), Gaussian(0.0, 1.0), 0.5, 100, beta=-1.0)


def test_expected_v_exceeds_certainty_equivalent() -> None:
    from lrc.lyapunov import expected_v, predicted_v

    model, ref = Gaussian(1.0, 0.8), Gaussian(0.0, 1.0)
    assert expected_v(model, ref, 0.5, 200) > predicted_v(model, ref, 0.5, 200)


def test_expected_v_noise_floor_is_order_one_over_n() -> None:
    """At full real data and perfect calibration the floor is ~1/n."""
    from lrc.lyapunov import expected_v

    ref = Gaussian(0.0, 1.0)
    n = 200
    floor = expected_v(ref, ref, alpha=1.0, n_fit=n)
    assert 0.5 / n < floor < 2.0 / n


def test_expected_v_beta_damps_noise_when_calibrated() -> None:
    """With no correction needed, KL-regularization is pure noise reduction."""
    from lrc.lyapunov import expected_v

    ref = Gaussian(0.0, 1.0)
    assert expected_v(ref, ref, 1.0, 200, beta=200.0) < expected_v(ref, ref, 1.0, 200, beta=0.0)


def test_expected_v_beta_dilutes_large_corrections() -> None:
    """When the model is far off, damping the update costs more than it saves."""
    from lrc.lyapunov import expected_v

    model, ref = Gaussian(2.0, 1.0), Gaussian(0.0, 1.0)
    assert expected_v(model, ref, 1.0, 200, beta=200.0) > expected_v(model, ref, 1.0, 200, beta=0.0)
