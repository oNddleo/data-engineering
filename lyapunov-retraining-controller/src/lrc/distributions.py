"""1-D Gaussian primitives: sampling, fitting, KL divergence, mixture moments.

Everything downstream (the simulator, the Lyapunov predictor, the controller)
is built on closed-form Gaussian algebra so the control law can be evaluated
exactly instead of by Monte Carlo. The two fitting flavours matter:

- ``fit_mle`` uses the population-variance estimator (divides by n). Its
  downward bias, E[sigma2_hat] = (1 - 1/n) * sigma2, is the engine of model
  collapse when a model is retrained on its own output: variance shrinks
  geometrically while the mean random-walks.
- ``fit_unbiased`` divides by n-1 and is used by the controller's monitoring
  probe, where we want an unbiased view of the reference distribution.

Failure mode guarded here: a degenerate (zero-variance) fit would make every
later KL infinite or undefined, so fitted variances are floored at
``SIGMA2_FLOOR``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import random
    from collections.abc import Sequence

SIGMA2_FLOOR = 1e-12


@dataclass(frozen=True)
class Gaussian:
    """An immutable 1-D Gaussian parameterised by mean and variance."""

    mu: float
    sigma2: float

    def __post_init__(self) -> None:
        if self.sigma2 <= 0.0:
            raise ValueError(f"sigma2 must be positive, got {self.sigma2}")

    @property
    def sigma(self) -> float:
        return math.sqrt(self.sigma2)

    def sample(self, rng: random.Random, n: int) -> list[float]:
        if n < 0:
            raise ValueError(f"n must be non-negative, got {n}")
        return [rng.gauss(self.mu, self.sigma) for _ in range(n)]


def kl_divergence(p: Gaussian, q: Gaussian) -> float:
    """KL(p || q) in nats; the Lyapunov function is V_t = KL(model || reference)."""
    return math.log(q.sigma / p.sigma) + (p.sigma2 + (p.mu - q.mu) ** 2) / (2.0 * q.sigma2) - 0.5


def fit_mle(xs: Sequence[float]) -> Gaussian:
    """Maximum-likelihood Gaussian fit (biased, /n variance)."""
    n = len(xs)
    if n < 2:
        raise ValueError(f"need at least 2 samples to fit, got {n}")
    mu = sum(xs) / n
    sigma2 = sum((x - mu) ** 2 for x in xs) / n
    return Gaussian(mu, max(sigma2, SIGMA2_FLOOR))


def fit_unbiased(xs: Sequence[float]) -> Gaussian:
    """Gaussian fit with the unbiased (/(n-1)) variance estimator."""
    n = len(xs)
    if n < 2:
        raise ValueError(f"need at least 2 samples to fit, got {n}")
    mu = sum(xs) / n
    sigma2 = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return Gaussian(mu, max(sigma2, SIGMA2_FLOOR))


def mixture_moments(real: Gaussian, model: Gaussian, w: float) -> Gaussian:
    """Moment-matched Gaussian of the mixture w*real + (1-w)*model.

    mu' = w*mu_r + (1-w)*mu_m
    sigma'^2 = w*sigma_r^2 + (1-w)*sigma_m^2 + w*(1-w)*(mu_r - mu_m)^2
    """
    if not 0.0 <= w <= 1.0:
        raise ValueError(f"w must be in [0, 1], got {w}")
    mu = w * real.mu + (1.0 - w) * model.mu
    sigma2 = w * real.sigma2 + (1.0 - w) * model.sigma2 + w * (1.0 - w) * (real.mu - model.mu) ** 2
    return Gaussian(mu, max(sigma2, SIGMA2_FLOOR))
