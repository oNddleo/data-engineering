"""The Lyapunov function and the exact one-step expectation map.

V_t = KL(model_t || reference_t). A retrain with real-data fraction w and
fit-sample size n maps the model state forward. With a deterministic split
of k = round(w*n) real samples and n-k synthetic samples, the MLE fit has

  E[mu_hat]     = w*mu_r + (1-w)*mu_m                                (exact)
  E[sigma2_hat] = (1 - 1/n) * sigma_bar^2 + w*(1-w)*(mu_r - mu_m)^2  (exact)

where sigma_bar^2 = w*sigma_r^2 + (1-w)*sigma_m^2. The (1 - 1/n) factor is
the MLE shrinkage that drives collapse at w = 0; the w*(1-w)*dmu^2 term is
the variance the mixture gains from mean disagreement. ``predicted_v`` plugs
the certainty-equivalent next state into KL — this is what the controller
minimises over w. It ignores estimator noise (Var[mu_hat] ~ sigma^2/n), which
is why the control law carries an additive slack c = O(1/n).

KL-regularization (the second knob): a retrain may shrink the fit toward the
previous model with weight beta pseudo-samples (``fit_regularized``), scaling
both the expected update and the fit-noise standard deviation by n/(n+beta).

``expected_v`` adds the two leading noise terms a certainty-equivalent
prediction drops — Var[mu_hat]/(2*sigma_r^2) from the mean and
Var[sigma2_hat]/(4*sigma_ce^4) from the variance (second-order KL expansion).
At perfect calibration and beta = 0 they sum to ~1/n, which is why the
controller's default slack is c = 2/n: just above the irreducible floor.
Choosing beta > 0 is only ever rational under ``expected_v`` — a CE predictor
sees beta's bias but not the noise it saves, and would always pick beta = 0.
"""

from __future__ import annotations

from .distributions import SIGMA2_FLOOR, Gaussian, kl_divergence


def effective_real_fraction(alpha: float, n_fit: int) -> float:
    """The realised real-data fraction after rounding to whole samples."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")
    if n_fit < 2:
        raise ValueError(f"n_fit must be >= 2, got {n_fit}")
    return round(alpha * n_fit) / n_fit


def predicted_next_state(
    model: Gaussian, real: Gaussian, alpha: float, n_fit: int, beta: float = 0.0
) -> Gaussian:
    """Certainty-equivalent model state after one retrain at real fraction alpha.

    With beta > 0 the fit is KL-regularized toward the current model: the
    expected MLE state is shrunk by n/(n+beta) pseudo-sample weighting.
    """
    if beta < 0.0:
        raise ValueError(f"beta must be non-negative, got {beta}")
    w = effective_real_fraction(alpha, n_fit)
    mu_mle = w * real.mu + (1.0 - w) * model.mu
    sigma_bar2 = w * real.sigma2 + (1.0 - w) * model.sigma2
    sigma2_mle = (1.0 - 1.0 / n_fit) * sigma_bar2 + w * (1.0 - w) * (real.mu - model.mu) ** 2
    mu = (n_fit * mu_mle + beta * model.mu) / (n_fit + beta)
    sigma2 = (n_fit * sigma2_mle + beta * model.sigma2) / (n_fit + beta)
    return Gaussian(mu, max(sigma2, SIGMA2_FLOOR))


def predicted_v(model: Gaussian, real: Gaussian, alpha: float, n_fit: int) -> float:
    """Predicted V after one retrain at real fraction alpha, measured against ``real``."""
    return kl_divergence(predicted_next_state(model, real, alpha, n_fit), real)


def fit_sample_variance(model: Gaussian, real: Gaussian, alpha: float, n_fit: int) -> float:
    """Population variance of a single draw from the retraining mixture."""
    w = effective_real_fraction(alpha, n_fit)
    return w * real.sigma2 + (1.0 - w) * model.sigma2 + w * (1.0 - w) * (real.mu - model.mu) ** 2


def expected_v(
    model: Gaussian, real: Gaussian, alpha: float, n_fit: int, beta: float = 0.0
) -> float:
    """E[V after retrain]: certainty-equivalent KL plus the leading noise terms.

    Var[mu_hat]    ~ (n/(n+beta))^2 * sigma_mix^2 / n      -> /(2*sigma_r^2)
    Var[sigma2_hat]~ (n/(n+beta))^2 * 2*sigma_mix^4 / n    -> /(4*sigma_ce^4)
    """
    ce = predicted_next_state(model, real, alpha, n_fit, beta)
    sigma_mix2 = fit_sample_variance(model, real, alpha, n_fit)
    shrink2 = (n_fit / (n_fit + beta)) ** 2
    var_mu = shrink2 * sigma_mix2 / n_fit
    var_sigma2 = shrink2 * 2.0 * sigma_mix2**2 / n_fit
    return (
        kl_divergence(ce, real) + var_mu / (2.0 * real.sigma2) + var_sigma2 / (4.0 * ce.sigma2**2)
    )


def lyapunov_value(model: Gaussian, real: Gaussian) -> float:
    """V = KL(model || real)."""
    return kl_divergence(model, real)
