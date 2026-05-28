"""Privacy accountants: Basic composition, RDP, and zCDP."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from privledger.mechanisms import RDP_ORDERS, GaussianMechanism, LaplaceMechanism

Mechanism = GaussianMechanism | LaplaceMechanism


@dataclass
class BasicCompositionAccountant:
    """Tracks total pure epsilon-DP spend via simple composition (sum)."""

    _total_epsilon: float = field(default=0.0, init=False)

    @property
    def total_epsilon(self) -> float:
        """Return cumulative epsilon spent."""
        return self._total_epsilon

    def spend(self, mechanism: Mechanism, delta: float = 1e-6) -> None:
        """Record a query spend."""
        if isinstance(mechanism, GaussianMechanism):
            self._total_epsilon += mechanism.dp_epsilon(delta)
        else:
            self._total_epsilon += mechanism.dp_epsilon()

    def epsilon(self, delta: float = 1e-6) -> float:  # noqa: ARG002
        """Return total epsilon (delta parameter kept for interface parity)."""
        return self._total_epsilon

    def can_afford(self, mechanism: Mechanism, budget_epsilon: float, delta: float = 1e-6) -> bool:
        """Return True if spending *mechanism* would stay within *budget_epsilon*."""
        if isinstance(mechanism, GaussianMechanism):
            cost = mechanism.dp_epsilon(delta)
        else:
            cost = mechanism.dp_epsilon()
        return self._total_epsilon + cost <= budget_epsilon

    def reset(self) -> None:
        """Zero out all accumulated spend."""
        self._total_epsilon = 0.0

    def copy(self) -> BasicCompositionAccountant:
        """Return a copy of this accountant."""
        acc = BasicCompositionAccountant()
        acc._total_epsilon = self._total_epsilon
        return acc


@dataclass
class RDPAccountant:
    """Tracks spend as an RDP curve over the standard alpha grid.

    Composition is additive per alpha.  Conversion to (epsilon, delta)-DP
    uses the standard bound: rdp(alpha) + log(1/delta) / (alpha - 1).
    """

    # list of (alpha, epsilon_rdp) accumulated spend per alpha
    _curve: dict[float, float] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._curve = {alpha: 0.0 for alpha in RDP_ORDERS}

    def spend(self, mechanism: Mechanism) -> None:
        """Record a query spend on the RDP curve.

        Only GaussianMechanism has natural RDP; for Laplace we use the
        standard RDP bound for Laplace mechanism: min(alpha, 1/(alpha-1)) * epsilon_dp^2 / 2,
        but as a conservative fallback we record the pure-DP epsilon at each alpha.
        """
        if isinstance(mechanism, GaussianMechanism):
            for alpha in RDP_ORDERS:
                self._curve[alpha] += mechanism.rdp_cost(alpha)
        else:
            # Laplace: epsilon-DP trivially implies RDP(alpha) = alpha * epsilon_dp for alpha>=1
            eps = mechanism.dp_epsilon()
            for alpha in RDP_ORDERS:
                self._curve[alpha] += eps  # conservative bound

    def epsilon(self, delta: float) -> float:
        """Convert accumulated RDP curve to (epsilon, delta)-DP epsilon."""
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")
        best = math.inf
        for alpha, rdp_eps in self._curve.items():
            if alpha <= 1.0:
                continue
            bound = rdp_eps + math.log(1.0 / delta) / (alpha - 1.0)
            best = min(best, bound)
        if math.isinf(best):
            return best
        return best

    def optimal_alpha(self, delta: float) -> float:
        """Return the alpha that achieves the tightest DP conversion."""
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")
        best_alpha = list(self._curve.keys())[0]
        best_val = math.inf
        for alpha, rdp_eps in self._curve.items():
            if alpha <= 1.0:
                continue
            bound = rdp_eps + math.log(1.0 / delta) / (alpha - 1.0)
            if bound < best_val:
                best_val = bound
                best_alpha = alpha
        return best_alpha

    def total_rdp(self, alpha: float) -> float:
        """Return total accumulated RDP epsilon at a specific order alpha."""
        return self._curve.get(alpha, 0.0)

    def can_afford(self, mechanism: Mechanism, budget_epsilon: float, delta: float) -> bool:
        """Return True if spending *mechanism* stays within the RDP-converted budget."""
        if isinstance(mechanism, GaussianMechanism):
            trial: dict[float, float] = {
                alpha: self._curve[alpha] + mechanism.rdp_cost(alpha) for alpha in RDP_ORDERS
            }
        else:
            eps = mechanism.dp_epsilon()
            trial = {alpha: self._curve[alpha] + eps for alpha in RDP_ORDERS}

        best = math.inf
        for alpha, rdp_eps in trial.items():
            if alpha <= 1.0:
                continue
            bound = rdp_eps + math.log(1.0 / delta) / (alpha - 1.0)
            best = min(best, bound)
        return best <= budget_epsilon

    def reset(self) -> None:
        """Zero out all accumulated spend."""
        self._curve = {alpha: 0.0 for alpha in RDP_ORDERS}

    def copy(self) -> RDPAccountant:
        """Return a copy of this accountant."""
        acc = RDPAccountant()
        acc._curve = dict(self._curve)
        return acc


@dataclass
class ZCDPAccountant:
    """Tracks spend as zCDP rho.  Composition is additive in rho.

    Conversion to (epsilon, delta)-DP via Balle et al. 2020:
        epsilon = rho + 2 * sqrt(rho * log(1/delta))
    """

    _total_rho: float = field(default=0.0, init=False)

    @property
    def total_rho(self) -> float:
        """Return cumulative rho."""
        return self._total_rho

    def spend(self, mechanism: Mechanism, delta: float = 1e-6) -> None:
        """Record a query spend in zCDP rho."""
        if isinstance(mechanism, GaussianMechanism):
            self._total_rho += mechanism.zcdp_rho()
        else:
            # Laplace mechanism: rho-zCDP conversion via pure-DP bound: rho = epsilon_dp^2 / 2
            eps = mechanism.dp_epsilon()
            self._total_rho += eps**2 / 2.0

    def epsilon(self, delta: float) -> float:
        """Convert accumulated rho to (epsilon, delta)-DP epsilon."""
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {delta}")
        rho = self._total_rho
        return rho + 2.0 * math.sqrt(rho * math.log(1.0 / delta))

    def can_afford(self, mechanism: Mechanism, budget_epsilon: float, delta: float) -> bool:
        """Return True if spending *mechanism* stays within the zCDP-converted budget."""
        if isinstance(mechanism, GaussianMechanism):
            trial_rho = self._total_rho + mechanism.zcdp_rho()
        else:
            eps = mechanism.dp_epsilon()
            trial_rho = self._total_rho + eps**2 / 2.0
        trial_eps = trial_rho + 2.0 * math.sqrt(trial_rho * math.log(1.0 / delta))
        return trial_eps <= budget_epsilon

    def reset(self) -> None:
        """Zero out all accumulated spend."""
        self._total_rho = 0.0

    def copy(self) -> ZCDPAccountant:
        """Return a copy of this accountant."""
        acc = ZCDPAccountant()
        acc._total_rho = self._total_rho
        return acc
