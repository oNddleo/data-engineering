"""Controllers: the Lyapunov drift condition and the baselines."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from lrc.controller import (
    FixedCadenceController,
    LyapunovController,
    NeverRetrainController,
)
from lrc.distributions import Gaussian
from lrc.lyapunov import lyapunov_value, predicted_v

REF = Gaussian(0.0, 1.0)


def test_never_controller_always_skips() -> None:
    c = NeverRetrainController()
    assert not c.decide(Gaussian(9.0, 0.1), REF, t=3).retrain


def test_fixed_cadence_fires_on_period() -> None:
    c = FixedCadenceController(period=5, alpha=0.7)
    assert c.decide(REF, REF, t=0).retrain
    assert not c.decide(REF, REF, t=1).retrain
    assert c.decide(REF, REF, t=10).retrain
    assert c.decide(REF, REF, t=10).alpha == pytest.approx(0.7)


def test_fixed_cadence_validates_params() -> None:
    with pytest.raises(ValueError):
        FixedCadenceController(period=0, alpha=0.5)
    with pytest.raises(ValueError):
        FixedCadenceController(period=1, alpha=2.0)


def test_lyapunov_validates_params() -> None:
    with pytest.raises(ValueError):
        LyapunovController(n_fit=100, eta=1.5)
    with pytest.raises(ValueError):
        LyapunovController(n_fit=1)


def test_lyapunov_defaults_derive_from_n_fit() -> None:
    c = LyapunovController(n_fit=200, eta=0.4)
    assert c.effective_slack == pytest.approx(0.01)
    assert c.effective_floor == pytest.approx(0.025)


def test_lyapunov_skips_when_v_below_floor() -> None:
    c = LyapunovController(n_fit=200)
    # Model essentially equal to reference: V ~ 0 < floor.
    assert not c.decide(Gaussian(0.001, 1.0), REF, t=0).retrain


def test_lyapunov_retrains_when_v_above_floor() -> None:
    c = LyapunovController(n_fit=200)
    action = c.decide(Gaussian(1.0, 1.0), REF, t=0)
    assert action.retrain
    assert 0.0 < action.alpha <= 1.0


def test_chosen_alpha_satisfies_drift_condition() -> None:
    """Deadbeat target c implies the classic (1 - eta) * V + c drift condition."""
    c = LyapunovController(n_fit=200, eta=0.3)
    model = Gaussian(1.5, 0.4)
    v = lyapunov_value(model, REF)
    action = c.decide(model, REF, t=0)
    v_next = predicted_v(model, REF, action.alpha, c.n_fit)
    assert v_next <= c.effective_slack + 1e-12  # deadbeat: back to the noise floor
    assert v_next <= (1.0 - c.eta) * v + c.effective_slack  # hence Foster-Lyapunov drift


def test_chosen_alpha_is_minimal_on_grid() -> None:
    """One grid notch less real data must miss the deadbeat target."""
    c = LyapunovController(n_fit=200, eta=0.3)
    model = Gaussian(2.0, 0.5)
    action = c.decide(model, REF, t=0)
    assert action.alpha > 0.0
    one_less = action.alpha - 1.0 / c.grid
    assert predicted_v(model, REF, one_less, c.n_fit) > c.effective_slack


def test_bigger_drift_demands_more_real_data() -> None:
    c = LyapunovController(n_fit=200, eta=0.3)
    a_small = c.decide(Gaussian(0.5, 1.0), REF, t=0).alpha
    a_large = c.decide(Gaussian(3.0, 1.0), REF, t=0).alpha
    assert a_large > a_small


@given(
    st.floats(min_value=-5, max_value=5),
    st.floats(min_value=0.01, max_value=5),
)
def test_lyapunov_action_always_valid(mu: float, sigma2: float) -> None:
    c = LyapunovController(n_fit=100, eta=0.3)
    action = c.decide(Gaussian(mu, sigma2), REF, t=0)
    assert 0.0 <= action.alpha <= 1.0


def test_controller_names_are_descriptive() -> None:
    assert "lyapunov" in LyapunovController(n_fit=100).name
    assert "fixed" in FixedCadenceController(period=5, alpha=0.5).name
    assert NeverRetrainController().name == "never"
