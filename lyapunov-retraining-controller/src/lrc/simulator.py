"""Generation-loop simulator: drifting reference distribution + retrained model.

The environment exposes the true reference Gaussian at each step (used only
for evaluation); controllers must estimate it through ``probe``, which costs
real samples. A retrain draws k = round(alpha * n_fit) fresh real samples and
n_fit - k synthetic samples from the current model, then refits by MLE — the
deterministic split keeps the controller's one-step prediction exact in
expectation and the tests stable.

Real-data accounting: both probes and the real share of retrains debit
``real_samples_used``. That budget is the cost axis the benchmark trades off
against stability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .distributions import Gaussian, fit_mle
from .lyapunov import lyapunov_value

if TYPE_CHECKING:
    import random

DriftKind = str  # "none" | "linear" | "shock"

_VALID_DRIFTS = ("none", "linear", "shock")


@dataclass(frozen=True)
class EnvironmentConfig:
    """Reference-distribution trajectory: static, linearly drifting mean, or a step shock."""

    mu0: float = 0.0
    sigma2: float = 1.0
    drift: DriftKind = "none"
    drift_rate: float = 0.0  # mean shift per step ("linear")
    shock_at: int = 0  # step index of the shock ("shock")
    shock_size: float = 0.0  # mean jump applied from shock_at onward

    def __post_init__(self) -> None:
        if self.drift not in _VALID_DRIFTS:
            raise ValueError(f"drift must be one of {_VALID_DRIFTS}, got {self.drift!r}")
        if self.sigma2 <= 0.0:
            raise ValueError(f"sigma2 must be positive, got {self.sigma2}")

    def reference_at(self, t: int) -> Gaussian:
        mu = self.mu0
        if self.drift == "linear":
            mu += self.drift_rate * t
        elif self.drift == "shock" and t >= self.shock_at:
            mu += self.shock_size
        return Gaussian(mu, self.sigma2)


@dataclass(frozen=True)
class RetrainAction:
    """One control decision: retrain or skip; alpha is the real-data fraction."""

    retrain: bool
    alpha: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {self.alpha}")


SKIP = RetrainAction(retrain=False)


@dataclass
class Simulator:
    """Steps the model/environment system forward under controller actions."""

    env: EnvironmentConfig
    n_fit: int
    rng: random.Random
    t: int = 0
    real_samples_used: int = 0
    retrain_count: int = 0
    model: Gaussian = field(init=False)

    def __post_init__(self) -> None:
        if self.n_fit < 2:
            raise ValueError(f"n_fit must be >= 2, got {self.n_fit}")
        # Start perfectly calibrated: V_0 = 0. Everything that follows is
        # degradation the controller must counteract.
        self.model = self.env.reference_at(0)

    @property
    def reference(self) -> Gaussian:
        return self.env.reference_at(self.t)

    def probe(self, m: int) -> list[float]:
        """Draw m fresh real samples for monitoring; debits the real budget."""
        self.real_samples_used += m
        return self.reference.sample(self.rng, m)

    def true_v(self) -> float:
        """Exact V against the true reference — evaluation only, not visible to controllers."""
        return lyapunov_value(self.model, self.reference)

    def step(self, action: RetrainAction) -> None:
        """Apply one action (retrain on the mixed corpus, or skip), then advance time."""
        if action.retrain:
            k = round(action.alpha * self.n_fit)
            data = self.reference.sample(self.rng, k)
            data += self.model.sample(self.rng, self.n_fit - k)
            self.real_samples_used += k
            self.retrain_count += 1
            self.model = fit_mle(data)
        self.t += 1
