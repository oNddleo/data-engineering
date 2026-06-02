"""Differential-privacy noise mechanisms — stdlib only (no NumPy)."""

from __future__ import annotations

import math
import random

# ── Laplace mechanism ─────────────────────────────────────────────────────────


def laplace_noise(sensitivity: float, epsilon: float, rng: random.Random | None = None) -> float:
    """Sample from Laplace(0, sensitivity/epsilon) via inverse-CDF.

    Uses the difference-of-exponentials identity:
        X = E₁ − E₂  where E₁, E₂ ~ Exp(ε/sensitivity)
    which avoids any direct uniform-to-Laplace transform.
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be positive, got {epsilon}")
    if sensitivity <= 0:
        raise ValueError(f"sensitivity must be positive, got {sensitivity}")
    _rng = rng or random.SystemRandom()
    scale = sensitivity / epsilon
    # exponential with rate 1/scale = exponential with mean `scale`
    e1 = _rng.expovariate(1.0 / scale)
    e2 = _rng.expovariate(1.0 / scale)
    return e1 - e2


def laplace_std(sensitivity: float, epsilon: float) -> float:
    """Standard deviation of Lap(0, sensitivity/epsilon)."""
    return math.sqrt(2.0) * sensitivity / epsilon


# ── Gaussian mechanism ────────────────────────────────────────────────────────


def _gaussian_sigma(sensitivity: float, epsilon: float, delta: float) -> float:
    """Compute σ for (ε, δ)-DP Gaussian mechanism (analytic formula)."""
    if epsilon <= 0:
        raise ValueError(f"epsilon must be positive, got {epsilon}")
    if not (0 < delta < 1):
        raise ValueError(f"delta must be in (0, 1), got {delta}")
    if sensitivity <= 0:
        raise ValueError(f"sensitivity must be positive, got {sensitivity}")
    return sensitivity * math.sqrt(2.0 * math.log(1.25 / delta)) / epsilon


def gaussian_noise(
    sensitivity: float,
    epsilon: float,
    delta: float,
    rng: random.Random | None = None,
) -> float:
    """Sample from N(0, σ²) where σ satisfies (ε, δ)-DP."""
    sigma = _gaussian_sigma(sensitivity, epsilon, delta)
    _rng = rng or random.SystemRandom()
    return _rng.gauss(0.0, sigma)


def gaussian_std(sensitivity: float, epsilon: float, delta: float) -> float:
    """Standard deviation of the Gaussian mechanism."""
    return _gaussian_sigma(sensitivity, epsilon, delta)


# ── Generic apply ─────────────────────────────────────────────────────────────


def apply_laplace(
    true_value: float,
    sensitivity: float,
    epsilon: float,
    rng: random.Random | None = None,
) -> tuple[float, float]:
    """Return (noisy_value, noise_added)."""
    noise = laplace_noise(sensitivity, epsilon, rng)
    return true_value + noise, noise


def apply_gaussian(
    true_value: float,
    sensitivity: float,
    epsilon: float,
    delta: float,
    rng: random.Random | None = None,
) -> tuple[float, float]:
    """Return (noisy_value, noise_added)."""
    noise = gaussian_noise(sensitivity, epsilon, delta, rng)
    return true_value + noise, noise


# ── Default sensitivity lookup ────────────────────────────────────────────────

_DEFAULT_SENSITIVITY: dict[str, float] = {
    "count": 1.0,
    "histogram": 1.0,
    "sum": 1.0,
    "mean": 1.0,
}


def default_sensitivity(query_type: str, data_range: float | None = None) -> float:
    """Global sensitivity for common aggregate query types."""
    if query_type in ("sum", "mean"):
        return data_range or 1.0
    return _DEFAULT_SENSITIVITY.get(query_type, 1.0)
