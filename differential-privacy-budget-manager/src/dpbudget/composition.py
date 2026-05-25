"""Composition theorems for differential privacy.

Provides tight (advanced) and basic composition bounds for sequences
of DP mechanisms applied to the same dataset.
"""

from __future__ import annotations

import math


def basic_compose_epsilon(epsilons: list[float]) -> float:
    """Basic composition: total ε = Σ εᵢ (pure DP)."""
    return sum(epsilons)


def advanced_compose_epsilon(epsilons: list[float], delta_prime: float) -> float:
    """Advanced composition theorem (Dwork et al., 2010).

    For k mechanisms each (εᵢ, 0)-DP, the composition is
    (ε*, δ')-DP where:
        ε* = Σ εᵢ(e^εᵢ − 1) / (e^εᵢ + 1)  +  sqrt(2 Σ εᵢ² · ln(1/δ'))

    Approximated here using the common simplified bound:
        ε* = sqrt(2k ln(1/δ')) · ε  (homogeneous case with ε = max εᵢ)

    For heterogeneous εᵢ, uses the tighter closed-form.
    """
    if delta_prime <= 0 or delta_prime >= 1:
        raise ValueError(f"delta_prime must be in (0,1), got {delta_prime}")
    k = len(epsilons)
    if k == 0:
        return 0.0
    sum_sq = sum(e * e for e in epsilons)
    # Tighter advanced composition bound
    eps_star = math.sqrt(2 * sum_sq * math.log(1.0 / delta_prime))
    return eps_star


def rdp_compose_epsilon(epsilons: list[float], alpha: float, delta: float) -> float:
    """Rényi DP composition then convert to (ε,δ)-DP.

    For Laplace mechanism: RDP order-α budget = ε^2 · α / 2  (approximately)
    Composition: total RDP = Σ RDP_i
    Conversion: ε(δ) = RDP_total − log(δ) / (α − 1)
    """
    if alpha <= 1:
        raise ValueError(f"alpha must be > 1, got {alpha}")
    rdp_total = sum(e * e * alpha / 2.0 for e in epsilons)
    eps_delta = rdp_total - math.log(delta) / (alpha - 1)
    return max(0.0, eps_delta)


def moments_accountant_sigma(
    target_epsilon: float,
    target_delta: float,
    n_queries: int,
    sensitivity: float = 1.0,
) -> float:
    """Estimate Gaussian σ needed for (ε,δ)-DP over n_queries queries.

    Uses the Gaussian mechanism σ = sensitivity · sqrt(2 ln(1.25/δ_per)) / ε_per
    where ε_per and δ_per are per-query budgets under advanced composition.
    """
    if n_queries <= 0:
        raise ValueError("n_queries must be positive")
    eps_per = target_epsilon / math.sqrt(2.0 * n_queries * math.log(1.0 / target_delta))
    delta_per = target_delta / (2.0 * n_queries)
    sigma = sensitivity * math.sqrt(2.0 * math.log(1.25 / delta_per)) / eps_per
    return sigma
