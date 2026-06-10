"""Gaussian algebra: KL, fitting, mixture moments."""

import math
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from lrc.distributions import (
    Gaussian,
    fit_mle,
    fit_unbiased,
    kl_divergence,
    mixture_moments,
)

finite_mu = st.floats(min_value=-50, max_value=50)
finite_sigma2 = st.floats(min_value=1e-3, max_value=100)


def test_gaussian_rejects_nonpositive_variance() -> None:
    with pytest.raises(ValueError):
        Gaussian(0.0, 0.0)
    with pytest.raises(ValueError):
        Gaussian(0.0, -1.0)


def test_gaussian_sigma_is_sqrt_of_variance() -> None:
    assert Gaussian(0.0, 4.0).sigma == pytest.approx(2.0)


def test_sample_length_and_determinism() -> None:
    g = Gaussian(1.0, 2.0)
    a = g.sample(random.Random(7), 100)
    b = g.sample(random.Random(7), 100)
    assert len(a) == 100
    assert a == b


def test_sample_rejects_negative_n() -> None:
    with pytest.raises(ValueError):
        Gaussian(0.0, 1.0).sample(random.Random(0), -1)


def test_kl_of_identical_distributions_is_zero() -> None:
    g = Gaussian(3.0, 0.5)
    assert kl_divergence(g, g) == pytest.approx(0.0, abs=1e-12)


@given(finite_mu, finite_sigma2, finite_mu, finite_sigma2)
def test_kl_is_nonnegative(mu_p: float, s2_p: float, mu_q: float, s2_q: float) -> None:
    p, q = Gaussian(mu_p, s2_p), Gaussian(mu_q, s2_q)
    assert kl_divergence(p, q) >= -1e-12


def test_kl_known_value() -> None:
    # KL(N(1,1) || N(0,1)) = 1/2
    assert kl_divergence(Gaussian(1.0, 1.0), Gaussian(0.0, 1.0)) == pytest.approx(0.5)


def test_kl_blows_up_as_model_variance_collapses() -> None:
    ref = Gaussian(0.0, 1.0)
    v_small = kl_divergence(Gaussian(0.0, 0.1), ref)
    v_tiny = kl_divergence(Gaussian(0.0, 1e-6), ref)
    assert v_tiny > v_small > 0.0


def test_fit_mle_exact_on_known_points() -> None:
    g = fit_mle([1.0, 2.0, 3.0, 4.0])
    assert g.mu == pytest.approx(2.5)
    assert g.sigma2 == pytest.approx(1.25)  # population variance


def test_fit_unbiased_uses_n_minus_1() -> None:
    g = fit_unbiased([1.0, 2.0, 3.0, 4.0])
    assert g.sigma2 == pytest.approx(1.25 * 4 / 3)


def test_fit_floors_degenerate_variance() -> None:
    g = fit_mle([2.0, 2.0, 2.0])
    assert g.sigma2 > 0.0


@pytest.mark.parametrize("fit", [fit_mle, fit_unbiased])
def test_fit_requires_two_samples(fit) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        fit([1.0])


def test_mixture_moments_endpoints() -> None:
    real, model = Gaussian(2.0, 1.0), Gaussian(-1.0, 4.0)
    assert mixture_moments(real, model, 1.0) == real
    assert mixture_moments(real, model, 0.0) == model


def test_mixture_moments_closed_form() -> None:
    real, model = Gaussian(2.0, 1.0), Gaussian(0.0, 3.0)
    m = mixture_moments(real, model, 0.25)
    assert m.mu == pytest.approx(0.5)
    assert m.sigma2 == pytest.approx(0.25 * 1.0 + 0.75 * 3.0 + 0.25 * 0.75 * 4.0)


def test_mixture_moments_matches_monte_carlo() -> None:
    rng = random.Random(42)
    real, model, w = Gaussian(1.0, 2.0), Gaussian(-1.0, 0.5), 0.3
    n = 200_000
    k = int(w * n)
    xs = real.sample(rng, k) + model.sample(rng, n - k)
    mu_mc = sum(xs) / n
    s2_mc = sum((x - mu_mc) ** 2 for x in xs) / n
    m = mixture_moments(real, model, w)
    assert mu_mc == pytest.approx(m.mu, abs=0.02)
    assert s2_mc == pytest.approx(m.sigma2, rel=0.02)


def test_mixture_moments_rejects_bad_weight() -> None:
    g = Gaussian(0.0, 1.0)
    with pytest.raises(ValueError):
        mixture_moments(g, g, 1.5)


@given(finite_mu, finite_sigma2, finite_mu, finite_sigma2, st.floats(min_value=0, max_value=1))
def test_mixture_variance_at_least_weighted_min(
    mu_r: float, s2_r: float, mu_m: float, s2_m: float, w: float
) -> None:
    m = mixture_moments(Gaussian(mu_r, s2_r), Gaussian(mu_m, s2_m), w)
    assert m.sigma2 >= min(s2_r, s2_m) - 1e-9
    assert math.isfinite(m.mu)


def test_fit_regularized_beta_zero_equals_mle() -> None:
    from lrc.distributions import fit_regularized

    xs = [1.0, 2.0, 3.0, 4.0]
    assert fit_regularized(xs, Gaussian(9.0, 9.0), beta=0.0) == fit_mle(xs)


def test_fit_regularized_large_beta_stays_near_prior() -> None:
    from lrc.distributions import fit_regularized

    prior = Gaussian(5.0, 2.0)
    g = fit_regularized([0.0, 0.1, -0.1, 0.05], prior, beta=1e9)
    assert g.mu == pytest.approx(prior.mu, abs=1e-6)
    assert g.sigma2 == pytest.approx(prior.sigma2, rel=1e-6)


def test_fit_regularized_closed_form() -> None:
    from lrc.distributions import fit_regularized

    xs = [1.0, 2.0, 3.0, 4.0]  # mle: mu=2.5, sigma2=1.25, n=4
    prior = Gaussian(0.5, 0.25)
    g = fit_regularized(xs, prior, beta=4.0)
    assert g.mu == pytest.approx((4 * 2.5 + 4 * 0.5) / 8)
    assert g.sigma2 == pytest.approx((4 * 1.25 + 4 * 0.25) / 8)


def test_fit_regularized_rejects_negative_beta() -> None:
    from lrc.distributions import fit_regularized

    with pytest.raises(ValueError):
        fit_regularized([1.0, 2.0], Gaussian(0.0, 1.0), beta=-1.0)
