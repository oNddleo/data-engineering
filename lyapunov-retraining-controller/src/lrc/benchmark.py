"""Episode runner and the controller-vs-baseline benchmark harness.

An episode is T closed-loop steps: probe the reference (monitoring cost),
let the controller decide, apply the action, record the TRUE Lyapunov value
(evaluation uses the exact reference; controllers only ever saw the probe
estimate). The reference estimate is fitted on a sliding window of the last
``PROBE_WINDOW`` probes — pooling cuts the monitor's noise floor ~Wx at the
price of W-step lag under drift, and without it the controller chases probe
noise. The benchmark aggregates episodes across seeds and reports the axes
that matter for the comparison:

- stability: mean / max / final V, collapse rate (any V > threshold)
- cost: real samples consumed (probes + retrain data), retrain count
- responsiveness: recovery time after a shock (steps until V is back
  under the recovery threshold)
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .distributions import fit_unbiased
from .simulator import EnvironmentConfig, Simulator

if TYPE_CHECKING:
    from .controller import Controller

COLLAPSE_THRESHOLD = 1.0  # nats; KL this large means the model is unusable
RECOVERY_THRESHOLD = 0.05  # nats; "recovered" after a shock
PROBE_WINDOW = 4  # probes pooled into the reference estimate


@dataclass(frozen=True)
class EpisodeResult:
    controller: str
    vs: tuple[float, ...]
    real_samples: int
    retrains: int
    recovery_steps: int | None  # None if no shock or never recovered

    @property
    def mean_v(self) -> float:
        return sum(self.vs) / len(self.vs)

    @property
    def max_v(self) -> float:
        return max(self.vs)

    @property
    def final_v(self) -> float:
        return self.vs[-1]

    @property
    def collapsed(self) -> bool:
        return self.max_v > COLLAPSE_THRESHOLD


def run_episode(
    controller: Controller,
    env: EnvironmentConfig,
    steps: int,
    n_fit: int,
    probe_size: int,
    seed: int,
) -> EpisodeResult:
    """Run one closed-loop episode and collect the true-V trajectory."""
    if steps < 1:
        raise ValueError(f"steps must be >= 1, got {steps}")
    sim = Simulator(env=env, n_fit=n_fit, rng=random.Random(seed))
    vs: list[float] = []
    window: deque[list[float]] = deque(maxlen=PROBE_WINDOW)
    for t in range(steps):
        window.append(sim.probe(probe_size))
        reference_estimate = fit_unbiased([x for probe in window for x in probe])
        action = controller.decide(sim.model, reference_estimate, t)
        sim.step(action)
        vs.append(sim.true_v())

    recovery: int | None = None
    if env.drift == "shock":
        recovery = _recovery_steps(vs, env.shock_at)
    return EpisodeResult(
        controller=controller.name,
        vs=tuple(vs),
        real_samples=sim.real_samples_used,
        retrains=sim.retrain_count,
        recovery_steps=recovery,
    )


def _recovery_steps(vs: list[float], shock_at: int) -> int | None:
    """Steps after the shock until V first drops back under RECOVERY_THRESHOLD."""
    for i in range(shock_at, len(vs)):
        if vs[i] < RECOVERY_THRESHOLD:
            return i - shock_at
    return None


@dataclass(frozen=True)
class AggregateResult:
    controller: str
    episodes: tuple[EpisodeResult, ...]

    @property
    def mean_v(self) -> float:
        return sum(e.mean_v for e in self.episodes) / len(self.episodes)

    @property
    def max_v(self) -> float:
        return max(e.max_v for e in self.episodes)

    @property
    def collapse_rate(self) -> float:
        return sum(1 for e in self.episodes if e.collapsed) / len(self.episodes)

    @property
    def mean_real_samples(self) -> float:
        return sum(e.real_samples for e in self.episodes) / len(self.episodes)

    @property
    def mean_retrains(self) -> float:
        return sum(e.retrains for e in self.episodes) / len(self.episodes)

    @property
    def mean_recovery(self) -> float | None:
        rec = [e.recovery_steps for e in self.episodes]
        if any(r is None for r in rec):
            return None  # at least one episode never recovered
        return sum(r for r in rec if r is not None) / len(rec)


def run_benchmark(
    controllers: list[Controller],
    env: EnvironmentConfig,
    steps: int,
    n_fit: int,
    probe_size: int,
    seeds: int,
) -> list[AggregateResult]:
    """Run every controller over the same seed set; same seeds = paired comparison."""
    results: list[AggregateResult] = []
    for controller in controllers:
        episodes = tuple(
            run_episode(controller, env, steps, n_fit, probe_size, seed) for seed in range(seeds)
        )
        results.append(AggregateResult(controller=controller.name, episodes=episodes))
    return results


def format_table(results: list[AggregateResult]) -> str:
    """Plain-text comparison table for the CLI and the README results section."""
    header = (
        f"{'controller':<22} {'mean V':>9} {'max V':>9} {'collapse%':>10} "
        f"{'real/step':>10} {'retrains':>9} {'recovery':>9}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        steps = len(r.episodes[0].vs)
        rec = "-" if r.mean_recovery is None else f"{r.mean_recovery:.1f}"
        lines.append(
            f"{r.controller:<22} {r.mean_v:>9.4f} {r.max_v:>9.4f} "
            f"{100.0 * r.collapse_rate:>9.0f}% {r.mean_real_samples / steps:>10.1f} "
            f"{r.mean_retrains:>9.1f} {rec:>9}"
        )
    return "\n".join(lines)
