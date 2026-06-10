"""Environment trajectories and the generation-loop simulator."""

import random

import pytest

from lrc.simulator import SKIP, EnvironmentConfig, RetrainAction, Simulator


def make_sim(env: EnvironmentConfig | None = None, seed: int = 0, n_fit: int = 100) -> Simulator:
    return Simulator(env=env or EnvironmentConfig(), n_fit=n_fit, rng=random.Random(seed))


def test_environment_static_reference_is_constant() -> None:
    env = EnvironmentConfig(mu0=1.0, sigma2=2.0)
    assert env.reference_at(0) == env.reference_at(500)


def test_environment_linear_drift() -> None:
    env = EnvironmentConfig(drift="linear", drift_rate=0.1)
    assert env.reference_at(10).mu == pytest.approx(1.0)


def test_environment_shock_applies_from_shock_step() -> None:
    env = EnvironmentConfig(drift="shock", shock_at=5, shock_size=3.0)
    assert env.reference_at(4).mu == pytest.approx(0.0)
    assert env.reference_at(5).mu == pytest.approx(3.0)


def test_environment_rejects_unknown_drift() -> None:
    with pytest.raises(ValueError):
        EnvironmentConfig(drift="chaos")


def test_action_validates_alpha() -> None:
    with pytest.raises(ValueError):
        RetrainAction(retrain=True, alpha=1.2)


def test_simulator_starts_calibrated() -> None:
    sim = make_sim()
    assert sim.true_v() == pytest.approx(0.0, abs=1e-12)


def test_skip_advances_time_without_touching_model() -> None:
    sim = make_sim()
    before = sim.model
    sim.step(SKIP)
    assert sim.t == 1
    assert sim.model == before
    assert sim.retrain_count == 0
    assert sim.real_samples_used == 0


def test_retrain_budget_counts_only_real_share() -> None:
    sim = make_sim(n_fit=100)
    sim.step(RetrainAction(retrain=True, alpha=0.3))
    assert sim.real_samples_used == 30
    assert sim.retrain_count == 1


def test_probe_debits_budget() -> None:
    sim = make_sim()
    xs = sim.probe(16)
    assert len(xs) == 16
    assert sim.real_samples_used == 16


def test_same_seed_reproduces_trajectory() -> None:
    def trajectory(seed: int) -> list[float]:
        sim = make_sim(seed=seed)
        out = []
        for _ in range(20):
            sim.step(RetrainAction(retrain=True, alpha=0.5))
            out.append(sim.true_v())
        return out

    assert trajectory(7) == trajectory(7)
    assert trajectory(7) != trajectory(8)


def test_pure_synthetic_retraining_collapses_variance() -> None:
    """The model-collapse mechanism: alpha=0 shrinks variance geometrically."""
    sim = make_sim(seed=1, n_fit=50)
    for _ in range(300):
        sim.step(RetrainAction(retrain=True, alpha=0.0))
    assert sim.model.sigma2 < 0.05  # started at 1.0
    assert sim.true_v() > 1.0  # V diverges


def test_pure_real_retraining_stays_near_reference() -> None:
    sim = make_sim(seed=2, n_fit=200)
    for _ in range(300):
        sim.step(RetrainAction(retrain=True, alpha=1.0))
    assert sim.true_v() < 0.05


def test_never_retraining_under_drift_diverges() -> None:
    env = EnvironmentConfig(drift="linear", drift_rate=0.05)
    sim = make_sim(env=env, seed=3)
    for _ in range(100):
        sim.step(SKIP)
    assert sim.true_v() > 1.0


def test_simulator_rejects_tiny_n_fit() -> None:
    with pytest.raises(ValueError):
        make_sim(n_fit=1)
