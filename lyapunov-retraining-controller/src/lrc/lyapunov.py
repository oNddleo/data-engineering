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


def predicted_next_state(model: Gaussian, real: Gaussian, alpha: float, n_fit: int) -> Gaussian:
    """Certainty-equivalent model state after one retrain at real fraction alpha."""
    w = effective_real_fraction(alpha, n_fit)
    mu = w * real.mu + (1.0 - w) * model.mu
    sigma_bar2 = w * real.sigma2 + (1.0 - w) * model.sigma2
    sigma2 = (1.0 - 1.0 / n_fit) * sigma_bar2 + w * (1.0 - w) * (real.mu - model.mu) ** 2
    return Gaussian(mu, max(sigma2, SIGMA2_FLOOR))


def predicted_v(model: Gaussian, real: Gaussian, alpha: float, n_fit: int) -> float:
    """Predicted V after one retrain at real fraction alpha, measured against ``real``."""
    return kl_divergence(predicted_next_state(model, real, alpha, n_fit), real)


def lyapunov_value(model: Gaussian, real: Gaussian) -> float:
    """V = KL(model || real)."""
    return kl_divergence(model, real)
