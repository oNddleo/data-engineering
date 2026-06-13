"""Closed-loop episodes and the controller-vs-baseline benchmark.

These are the results-section claims, pinned as tests:
1. fixed-cadence at low alpha collapses under its own synthetic feedback;
2. the Lyapunov controller stays stable in the same environment;
3. under drift, the controller beats every fixed cadence on mean V without
   spending more real data than the heaviest baseline.
"""

import pytest

from lrc.benchmark import (
    COLLAPSE_THRESHOLD,
    AggregateResult,
    format_table,
    run_benchmark,
    run_episode,
)
from lrc.controller import (
    FixedCadenceController,
    LyapunovController,
    NeverRetrainController,
)
from lrc.simulator import EnvironmentConfig

N_FIT = 200
PROBE = 32


def test_run_episode_shapes_and_budget() -> None:
    env = EnvironmentConfig()
    r = run_episode(NeverRetrainController(), env, steps=50, n_fit=N_FIT, probe_size=PROBE, seed=0)
    assert len(r.vs) == 50
    assert r.retrains == 0
    assert r.real_samples == 50 * PROBE  # probes only
    assert r.recovery_steps is None  # no shock configured


def test_run_episode_rejects_zero_steps() -> None:
    with pytest.raises(ValueError):
        run_episode(NeverRetrainController(), EnvironmentConfig(), 0, N_FIT, PROBE, 0)


def test_episode_is_deterministic_per_seed() -> None:
    env = EnvironmentConfig(drift="linear", drift_rate=0.02)
    c = LyapunovController(n_fit=N_FIT)
    a = run_episode(c, env, 100, N_FIT, PROBE, seed=5)
    b = run_episode(c, env, 100, N_FIT, PROBE, seed=5)
    assert a.vs == b.vs


def test_fixed_cadence_low_alpha_collapses_static_env() -> None:
    """Naive retraining ON A SCHEDULE is what destabilises a calibrated model."""
    env = EnvironmentConfig()
    c = FixedCadenceController(period=1, alpha=0.05)
    r = run_episode(c, env, steps=400, n_fit=50, probe_size=PROBE, seed=1)
    assert r.collapsed


def test_lyapunov_stays_stable_static_env() -> None:
    env = EnvironmentConfig()
    c = LyapunovController(n_fit=N_FIT)
    r = run_episode(c, env, steps=400, n_fit=N_FIT, probe_size=PROBE, seed=1)
    assert not r.collapsed
    assert r.max_v < COLLAPSE_THRESHOLD / 4


def test_lyapunov_mostly_skips_when_static() -> None:
    """No drift means no work: the controller should retrain rarely."""
    env = EnvironmentConfig()
    c = LyapunovController(n_fit=N_FIT)
    r = run_episode(c, env, steps=200, n_fit=N_FIT, probe_size=PROBE, seed=3)
    assert r.retrains < 40


def test_lyapunov_tracks_linear_drift() -> None:
    env = EnvironmentConfig(drift="linear", drift_rate=0.02)
    c = LyapunovController(n_fit=N_FIT)
    r = run_episode(c, env, steps=200, n_fit=N_FIT, probe_size=PROBE, seed=2)
    assert not r.collapsed
    assert r.mean_v < 0.1


def test_lyapunov_recovers_from_shock_faster_than_baselines() -> None:
    env = EnvironmentConfig(drift="shock", shock_at=50, shock_size=2.0)
    lyap = run_episode(LyapunovController(n_fit=N_FIT), env, 150, N_FIT, PROBE, seed=4)
    fixed = run_episode(FixedCadenceController(period=5, alpha=0.5), env, 150, N_FIT, PROBE, seed=4)
    assert lyap.recovery_steps is not None
    assert lyap.recovery_steps <= 5
    assert fixed.recovery_steps is not None
    assert lyap.recovery_steps < fixed.recovery_steps


def test_lyapunov_beats_fixed_cadence_under_drift() -> None:
    """The headline benchmark claim, pinned with fixed seeds.

    Strict mean-V dominance over the sparse/heavy and dense/dilute cadences;
    against the well-tuned fixed(k=5, a=0.5) it matches mean V while spending
    strictly less real data.
    """
    env = EnvironmentConfig(drift="linear", drift_rate=0.02)
    lyap = LyapunovController(n_fit=N_FIT)
    tuned = FixedCadenceController(period=5, alpha=0.5)
    sparse = FixedCadenceController(period=20, alpha=1.0)
    dense = FixedCadenceController(period=1, alpha=0.1)
    results = run_benchmark(
        [lyap, tuned, sparse, dense], env, steps=200, n_fit=N_FIT, probe_size=PROBE, seeds=10
    )
    by_name = {r.controller: r for r in results}
    lyap_res = by_name[lyap.name]
    assert lyap_res.collapse_rate == 0.0
    for b in (sparse, dense):
        assert lyap_res.mean_v < by_name[b.name].mean_v
    tuned_res = by_name[tuned.name]
    assert lyap_res.mean_v <= tuned_res.mean_v * 1.1
    assert lyap_res.mean_real_samples < tuned_res.mean_real_samples


def test_aggregate_metrics_consistency() -> None:
    env = EnvironmentConfig(drift="shock", shock_at=20, shock_size=2.0)
    results = run_benchmark(
        [LyapunovController(n_fit=N_FIT)], env, steps=60, n_fit=N_FIT, probe_size=PROBE, seeds=3
    )
    agg = results[0]
    assert isinstance(agg, AggregateResult)
    assert len(agg.episodes) == 3
    assert agg.max_v >= agg.mean_v
    assert 0.0 <= agg.collapse_rate <= 1.0


def test_format_table_lists_all_controllers() -> None:
    env = EnvironmentConfig()
    controllers = [NeverRetrainController(), LyapunovController(n_fit=N_FIT)]
    results = run_benchmark(controllers, env, steps=30, n_fit=N_FIT, probe_size=PROBE, seeds=2)
    table = format_table(results)
    assert "never" in table
    assert "lyapunov" in table
    assert "mean V" in table


def test_dpp_budget_monotone_in_lam() -> None:
    """Higher data price -> less data bought. The frontier's x-axis."""
    from lrc.controller import DriftPlusPenaltyController

    env = EnvironmentConfig(drift="linear", drift_rate=0.02)
    cheap = DriftPlusPenaltyController(n_fit=N_FIT, lam=5e-5)
    pricey = DriftPlusPenaltyController(n_fit=N_FIT, lam=1e-3)
    results = run_benchmark([cheap, pricey], env, steps=100, n_fit=N_FIT, probe_size=PROBE, seeds=3)
    by_name = {r.controller: r for r in results}
    assert by_name[cheap.name].mean_real_samples > by_name[pricey.name].mean_real_samples
    assert by_name[cheap.name].mean_v < by_name[pricey.name].mean_v


def test_dpp_never_retrains_when_static_and_lam_high() -> None:
    """The implicit band: near the noise floor no retrain pays for itself."""
    from lrc.controller import DriftPlusPenaltyController

    c = DriftPlusPenaltyController(n_fit=N_FIT, lam=1e-3)
    r = run_episode(c, EnvironmentConfig(), steps=200, n_fit=N_FIT, probe_size=PROBE, seed=0)
    assert r.retrains == 0


def test_beta_rescues_dense_dilute_cadence_when_static() -> None:
    """KL-regularization damps the per-step fit-noise tax of naive dense retraining."""
    plain = FixedCadenceController(period=1, alpha=0.1)
    damped = FixedCadenceController(period=1, alpha=0.1, beta=2.0 * N_FIT)
    env = EnvironmentConfig()
    results = run_benchmark([plain, damped], env, steps=200, n_fit=N_FIT, probe_size=PROBE, seeds=5)
    by_name = {r.controller: r for r in results}
    assert by_name[damped.name].mean_v < by_name[plain.name].mean_v / 2.0


def test_beta_slows_shock_recovery() -> None:
    """The flip side: damping cripples responsiveness after a step change."""
    plain = FixedCadenceController(period=1, alpha=0.1)
    damped = FixedCadenceController(period=1, alpha=0.1, beta=2.0 * N_FIT)
    env = EnvironmentConfig(drift="shock", shock_at=50, shock_size=2.0)
    r_plain = run_episode(plain, env, 200, N_FIT, PROBE, seed=1)
    r_damped = run_episode(damped, env, 200, N_FIT, PROBE, seed=1)
    assert r_plain.recovery_steps is not None
    assert r_damped.recovery_steps is not None
    assert r_damped.recovery_steps > r_plain.recovery_steps


def test_dpp_uses_beta_only_in_frequent_retrain_regime() -> None:
    """lam large -> rare decisive retrains, beta = 0; lam tiny -> damped corrections."""
    import random as _random
    from collections import deque

    from lrc.controller import DriftPlusPenaltyController
    from lrc.distributions import fit_unbiased
    from lrc.simulator import Simulator

    def beta_counts(lam: float) -> tuple[int, int]:
        c = DriftPlusPenaltyController(n_fit=N_FIT, lam=lam)
        sim = Simulator(env=EnvironmentConfig(), n_fit=N_FIT, rng=_random.Random(0))
        window: deque[list[float]] = deque(maxlen=4)
        with_beta = without_beta = 0
        for t in range(200):
            window.append(sim.probe(PROBE))
            ref = fit_unbiased([x for p in window for x in p])
            action = c.decide(sim.model, ref, t)
            if action.retrain:
                if action.beta > 0:
                    with_beta += 1
                else:
                    without_beta += 1
            sim.step(action)
        return with_beta, without_beta

    with_beta_rare, _ = beta_counts(2e-4)
    with_beta_freq, without_beta_freq = beta_counts(1e-5)
    assert with_beta_rare == 0
    assert with_beta_freq > without_beta_freq
