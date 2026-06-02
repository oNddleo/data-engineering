"""Gaussian and Laplace mechanisms with RDP / zCDP / DP-epsilon cost computation."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Standard RDP orders used throughout the library.
RDP_ORDERS: tuple[float, ...] = (1.5, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 256.0, 1024.0, 1e6)


@dataclass(frozen=True)
class GaussianMechanism:
    """Gaussian mechanism parameterised by L2-sensitivity and noise std-dev sigma.

    Privacy accounting formulas:
    - RDP at order alpha: alpha * sensitivity^2 / (2 * sigma^2)
    - zCDP rho:           sensitivity^2 / (2 * sigma^2)
    - DP epsilon at delta (Balle et al. 2020 conversion from zCDP):
          rho + 2 * sqrt(rho * log(1/delta))
    """

    sensitivity: float
    sigma: float

    def __post_init__(self) -> None:
        if self.sensitivity <= 0:
            raise ValueError(f"sensitivity must be > 0, got {self.sensitivity}")
        if self.sigma <= 0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")

    # ------------------------------------------------------------------
    # Core cost quantities
    # ------------------------------------------------------------------

    def rdp_cost(self, alpha: float) -> float:
        """Return RDP epsilon at order *alpha*."""
        return alpha * self.sensitivity**2 / (2.0 * self.sigma**2)

    def zcdp_rho(self) -> float:
        """Return zCDP rho cost."""
        return self.sensitivity**2 / (2.0 * self.sigma**2)

    def dp_epsilon(self, delta: float) -> float:
        """Return (epsilon, delta)-DP epsilon via Balle et al. 2020 zCDP conversion."""
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")
        rho = self.zcdp_rho()
        return rho + 2.0 * math.sqrt(rho * math.log(1.0 / delta))

    def rdp_costs(self) -> list[tuple[float, float]]:
        """Return [(alpha, rdp_epsilon)] for all standard RDP orders."""
        return [(alpha, self.rdp_cost(alpha)) for alpha in RDP_ORDERS]

    # ------------------------------------------------------------------
    # Conversion: best RDP order → (epsilon, delta)-DP
    # ------------------------------------------------------------------

    def rdp_to_dp_epsilon(self, delta: float) -> float:
        """Convert RDP curve to (epsilon, delta)-DP epsilon using the best alpha.

        Formula (simplified standard bound):
            min_alpha { rdp(alpha) + log(1/delta) / (alpha - 1) }
        """
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")
        best = math.inf
        for alpha in RDP_ORDERS:
            if alpha <= 1.0:
                continue
            eps = self.rdp_cost(alpha) + math.log(1.0 / delta) / (alpha - 1.0)
            best = min(best, eps)
        return best


@dataclass(frozen=True)
class LaplaceMechanism:
    """Laplace mechanism parameterised by L1-sensitivity and scale *b*.

    epsilon-DP cost: sensitivity / b
    """

    sensitivity: float
    b: float

    def __post_init__(self) -> None:
        if self.sensitivity <= 0:
            raise ValueError(f"sensitivity must be > 0, got {self.sensitivity}")
        if self.b <= 0:
            raise ValueError(f"b must be > 0, got {self.b}")

    def dp_epsilon(self) -> float:
        """Return pure epsilon-DP cost."""
        return self.sensitivity / self.b
