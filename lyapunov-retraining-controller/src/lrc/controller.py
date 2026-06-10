"""Retraining controllers: the Lyapunov control law and fixed-cadence baselines.

``LyapunovController`` is a trigger + deadbeat law. While the estimated
Lyapunov value sits inside the band (V_hat <= trigger = c / eta) it does
nothing; once V_hat crosses the trigger it picks the SMALLEST real-data
fraction alpha whose predicted next value lands back at the noise floor:

    V_pred(alpha) <= c        (deadbeat target)

Because c <= (1 - eta) * V_hat + c always holds, every action satisfies the
classic drift condition V_pred <= (1 - eta) * V_hat + c with margin, giving
the Foster-Lyapunov bound lim sup E[V_t] <= c / eta + per-step drift — the
prescriptive payoff of the control-systems framing.

Why deadbeat instead of contracting V by (1 - eta) each step: every retrain
pays an O(1/n) fit-noise tax regardless of alpha, so many small corrections
cost more noise (and more real data) than rare decisive ones. The earlier
proportional variant retrained ~130 times in 200 drift steps and still
tracked worse than fixed(k=5); the band makes retraining frequency
self-adjust to the drift rate instead.

Controllers never see the true reference; they see an estimate fitted from a
monitoring probe window. The slack c absorbs estimator noise in V_hat plus
the O(1/n) terms the certainty-equivalent prediction ignores; the default
2 / n_fit sits just above that floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .lyapunov import expected_v, lyapunov_value, predicted_v
from .simulator import SKIP, RetrainAction

if TYPE_CHECKING:
    from .distributions import Gaussian


class Controller(Protocol):
    """Decides each step whether/how to retrain, from estimated state only."""

    @property
    def name(self) -> str: ...

    def decide(self, model: Gaussian, reference_estimate: Gaussian, t: int) -> RetrainAction: ...


@dataclass(frozen=True)
class NeverRetrainController:
    """Lower-cost bound: never retrain. Fine when static, diverges under drift."""

    @property
    def name(self) -> str:
        return "never"

    def decide(self, model: Gaussian, reference_estimate: Gaussian, t: int) -> RetrainAction:
        return SKIP


@dataclass(frozen=True)
class FixedCadenceController:
    """The naive baseline: retrain every ``period`` steps at a fixed real fraction.

    beta > 0 adds KL-regularization toward the previous model on every
    retrain — the ablation knob that rescues dense dilute cadences from
    their own fit noise.
    """

    period: int
    alpha: float
    beta: float = 0.0

    def __post_init__(self) -> None:
        if self.period < 1:
            raise ValueError(f"period must be >= 1, got {self.period}")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {self.alpha}")
        if self.beta < 0.0:
            raise ValueError(f"beta must be non-negative, got {self.beta}")

    @property
    def name(self) -> str:
        suffix = f",b={self.beta:g}" if self.beta > 0.0 else ""
        return f"fixed(k={self.period},a={self.alpha:g}{suffix})"

    def decide(self, model: Gaussian, reference_estimate: Gaussian, t: int) -> RetrainAction:
        if t % self.period == 0:
            return RetrainAction(retrain=True, alpha=self.alpha, beta=self.beta)
        return SKIP


@dataclass(frozen=True)
class LyapunovController:
    """Trigger + deadbeat: act when V crosses c/eta, restore V to the noise floor c."""

    n_fit: int
    eta: float = 0.3
    slack: float | None = None  # noise-floor target c; defaults to 2 / n_fit
    v_floor: float | None = None  # trigger; defaults to slack / eta
    grid: int = 256  # alpha search resolution

    def __post_init__(self) -> None:
        if not 0.0 < self.eta < 1.0:
            raise ValueError(f"eta must be in (0, 1), got {self.eta}")
        if self.n_fit < 2:
            raise ValueError(f"n_fit must be >= 2, got {self.n_fit}")
        if self.grid < 2:
            raise ValueError(f"grid must be >= 2, got {self.grid}")

    @property
    def name(self) -> str:
        return f"lyapunov(eta={self.eta:g})"

    @property
    def effective_slack(self) -> float:
        return 2.0 / self.n_fit if self.slack is None else self.slack

    @property
    def effective_floor(self) -> float:
        return self.effective_slack / self.eta if self.v_floor is None else self.v_floor

    def decide(self, model: Gaussian, reference_estimate: Gaussian, t: int) -> RetrainAction:
        v_hat = lyapunov_value(model, reference_estimate)
        if v_hat <= self.effective_floor:
            return SKIP
        target = self.effective_slack  # deadbeat: back to the noise floor
        # Smallest grid alpha meeting the target. A grid scan (not bisection)
        # because predicted V is not guaranteed monotone in alpha when the
        # model variance has collapsed below the reference's.
        for i in range(self.grid + 1):
            alpha = i / self.grid
            if predicted_v(model, reference_estimate, alpha, self.n_fit) <= target:
                return RetrainAction(retrain=True, alpha=alpha)
        # Unreachable in practice (alpha=1 maps V to ~1/(2n)); fail safe loud.
        return RetrainAction(retrain=True, alpha=1.0)


@dataclass(frozen=True)
class DriftPlusPenaltyController:
    """Neely-style drift-plus-penalty: per-step argmin of E[dV] + lam * real samples.

    Each step it evaluates every (alpha, beta) candidate on the noise-aware
    expected-V map and picks the action minimising

        [E[V_next] - V_hat] + lam * round(alpha * n_fit)

    against the skip baseline of 0. There is no trigger band — lam creates
    one implicitly: near the noise floor no retrain can buy enough V
    reduction to pay its data cost. Sweeping lam traces the cost-stability
    Pareto frontier (lam -> 0: stability at any cost; lam large: stingy).

    beta candidates cost nothing in real samples, so the optimizer uses
    KL-regularization whenever the noise it saves beats the correction it
    dilutes — this is the only controller that exercises the second knob.
    """

    n_fit: int
    lam: float  # nats per real sample
    beta_fracs: tuple[float, ...] = (0.0, 0.25, 1.0)  # beta = frac * n_fit
    grid: int = 64  # alpha search resolution

    def __post_init__(self) -> None:
        if self.lam <= 0.0:
            raise ValueError(f"lam must be positive, got {self.lam}")
        if self.n_fit < 2:
            raise ValueError(f"n_fit must be >= 2, got {self.n_fit}")
        if self.grid < 2:
            raise ValueError(f"grid must be >= 2, got {self.grid}")
        if any(f < 0.0 for f in self.beta_fracs) or not self.beta_fracs:
            raise ValueError(
                f"beta_fracs must be non-empty and non-negative, got {self.beta_fracs}"
            )

    @property
    def name(self) -> str:
        return f"dpp(lam={self.lam:g})"

    def decide(self, model: Gaussian, reference_estimate: Gaussian, t: int) -> RetrainAction:
        v_hat = lyapunov_value(model, reference_estimate)
        best_objective = 0.0  # skip: V unchanged, no cost
        best_action = SKIP
        for i in range(1, self.grid + 1):
            alpha = i / self.grid
            cost = self.lam * round(alpha * self.n_fit)
            for frac in self.beta_fracs:
                beta = frac * self.n_fit
                objective = (
                    expected_v(model, reference_estimate, alpha, self.n_fit, beta) - v_hat + cost
                )
                if objective < best_objective:
                    best_objective = objective
                    best_action = RetrainAction(retrain=True, alpha=alpha, beta=beta)
        return best_action
