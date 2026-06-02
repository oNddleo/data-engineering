"""QueryPlanner: accept / rewrite (binary-search sigma) / reject queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from privledger.mechanisms import GaussianMechanism

PlanDecision = Literal["accept", "rewrite", "reject"]

# Number of bisection steps for sigma search
_BISECTION_STEPS = 50


@dataclass
class QueryRequest:
    """Represents an incoming query to be planned."""

    query_id: str
    dataset: str
    analyst: str
    sensitivity: float
    sigma: float
    delta: float = 1e-6

    def __post_init__(self) -> None:
        if self.sensitivity <= 0:
            raise ValueError(f"sensitivity must be > 0, got {self.sensitivity}")
        if self.sigma <= 0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")
        if not (0.0 < self.delta < 1.0):
            raise ValueError(f"delta must be in (0, 1), got {self.delta}")


@dataclass
class QueryPlanner:
    """Plans queries against a remaining epsilon budget.

    Decisions:
    - accept  : the requested sigma fits within *budget_remaining*.
    - rewrite : a larger sigma can be found via binary search that fits.
    - reject  : even the maximum sigma (1000 * sensitivity) does not fit.
    """

    def plan(
        self,
        query: QueryRequest,
        budget_remaining: float,
    ) -> tuple[PlanDecision, float | None]:
        """Return (decision, sigma).

        - ``("accept", query.sigma)`` if the query fits as-is.
        - ``("rewrite", new_sigma)`` if a larger sigma was found.
        - ``("reject", None)`` if no sigma fits.

        *budget_remaining* is the epsilon budget remaining (basic composition),
        but the planner checks the Gaussian mechanism's DP-epsilon.
        """
        if budget_remaining <= 0.0:
            return "reject", None

        mechanism = GaussianMechanism(query.sensitivity, query.sigma)
        cost = mechanism.dp_epsilon(query.delta)

        if cost <= budget_remaining:
            return "accept", query.sigma

        # Binary search for smallest sigma in [sensitivity, 1000*sensitivity]
        lo = query.sensitivity
        hi = 1000.0 * query.sensitivity

        # Check if even maximum sigma fits
        max_mech = GaussianMechanism(query.sensitivity, hi)
        if max_mech.dp_epsilon(query.delta) > budget_remaining:
            return "reject", None

        for _ in range(_BISECTION_STEPS):
            mid = (lo + hi) / 2.0
            mid_mech = GaussianMechanism(query.sensitivity, mid)
            if mid_mech.dp_epsilon(query.delta) <= budget_remaining:
                hi = mid
            else:
                lo = mid

        # hi is the smallest sigma that fits
        return "rewrite", hi
