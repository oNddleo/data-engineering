"""Lyapunov-based retraining controller.

Treats periodic model retraining on a real/synthetic data mixture as a
discrete-time control system, with V_t = KL(model || reference) as the
Lyapunov function. The controller picks the cheapest real-data fraction that
forces V to contract, and is benchmarked against naive fixed-cadence
retraining.
"""

from .benchmark import (
    AggregateResult,
    EpisodeResult,
    format_table,
    run_benchmark,
    run_episode,
)
from .controller import (
    Controller,
    DriftPlusPenaltyController,
    FixedCadenceController,
    LyapunovController,
    NeverRetrainController,
)
from .distributions import (
    Gaussian,
    fit_mle,
    fit_regularized,
    fit_unbiased,
    kl_divergence,
    mixture_moments,
)
from .lyapunov import expected_v, lyapunov_value, predicted_next_state, predicted_v
from .simulator import SKIP, EnvironmentConfig, RetrainAction, Simulator

__version__ = "0.2.0"

__all__ = [
    "SKIP",
    "AggregateResult",
    "Controller",
    "DriftPlusPenaltyController",
    "EnvironmentConfig",
    "EpisodeResult",
    "FixedCadenceController",
    "Gaussian",
    "LyapunovController",
    "NeverRetrainController",
    "RetrainAction",
    "Simulator",
    "__version__",
    "expected_v",
    "fit_mle",
    "fit_regularized",
    "fit_unbiased",
    "format_table",
    "kl_divergence",
    "lyapunov_value",
    "mixture_moments",
    "predicted_next_state",
    "predicted_v",
    "run_benchmark",
    "run_episode",
]
