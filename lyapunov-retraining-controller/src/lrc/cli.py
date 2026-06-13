"""CLI: lrcctl info | run | benchmark | frontier.

``run`` prints a single closed-loop trajectory; ``benchmark`` reproduces the
README results tables; ``frontier`` sweeps the drift-plus-penalty weight lam
to trace the cost-stability Pareto frontier.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from . import __version__
from .benchmark import format_table, run_benchmark, run_episode
from .controller import (
    Controller,
    DriftPlusPenaltyController,
    FixedCadenceController,
    LyapunovController,
    NeverRetrainController,
)
from .simulator import EnvironmentConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

_SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(vs: Sequence[float], cap: float = 1.0) -> str:
    return "".join(_SPARK[min(int(min(v, cap) / cap * 7.999), 7)] for v in vs)


def _env_from_args(args: argparse.Namespace) -> EnvironmentConfig:
    return EnvironmentConfig(
        mu0=0.0,
        sigma2=1.0,
        drift=args.drift,
        drift_rate=args.drift_rate,
        shock_at=args.shock_at,
        shock_size=args.shock_size,
    )


def _controller_from_args(args: argparse.Namespace) -> Controller:
    if args.controller == "lyapunov":
        return LyapunovController(n_fit=args.n_fit, eta=args.eta)
    if args.controller == "dpp":
        return DriftPlusPenaltyController(n_fit=args.n_fit, lam=args.lam)
    if args.controller == "never":
        return NeverRetrainController()
    return FixedCadenceController(period=args.period, alpha=args.alpha, beta=args.beta)


def _add_env_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--drift", choices=["none", "linear", "shock"], default="none")
    p.add_argument("--drift-rate", type=float, default=0.02)
    p.add_argument("--shock-at", type=int, default=50)
    p.add_argument("--shock-size", type=float, default=2.0)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--n-fit", type=int, default=200)
    p.add_argument("--probe-size", type=int, default=32)


def cmd_info(_: argparse.Namespace) -> int:
    print(f"lyapunov-retraining-controller {__version__}")
    print("Lyapunov-based retraining controller vs naive fixed-cadence retraining.")
    print("V_t = KL(model_t || reference_t); when V crosses the trigger c/eta the")
    print("control law picks the cheapest real-data fraction alpha with V_pred <= c,")
    print("which guarantees the drift condition V_pred <= (1 - eta) * V + c.")
    print("Commands: info | run | benchmark")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    env = _env_from_args(args)
    controller = _controller_from_args(args)
    result = run_episode(controller, env, args.steps, args.n_fit, args.probe_size, args.seed)
    print(f"controller : {result.controller}")
    print(f"drift      : {env.drift}")
    print(f"V trajectory (0..{1.0:g} nats, {args.steps} steps):")
    print(f"  {_sparkline(result.vs)}")
    print(f"mean V     : {result.mean_v:.4f}")
    print(f"max V      : {result.max_v:.4f}")
    print(f"final V    : {result.final_v:.4f}")
    print(f"collapsed  : {result.collapsed}")
    print(f"retrains   : {result.retrains}/{args.steps}")
    print(
        f"real used  : {result.real_samples} samples ({result.real_samples / args.steps:.1f}/step)"
    )
    if result.recovery_steps is not None:
        print(f"recovery   : {result.recovery_steps} steps after shock")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    env = _env_from_args(args)
    controllers: list[Controller] = [
        NeverRetrainController(),
        FixedCadenceController(period=1, alpha=0.1),
        FixedCadenceController(period=5, alpha=0.5),
        FixedCadenceController(period=20, alpha=1.0),
        LyapunovController(n_fit=args.n_fit, eta=args.eta),
        DriftPlusPenaltyController(n_fit=args.n_fit, lam=args.lam),
    ]
    results = run_benchmark(controllers, env, args.steps, args.n_fit, args.probe_size, args.seeds)
    print(
        f"environment: drift={env.drift}  steps={args.steps}  n_fit={args.n_fit}  seeds={args.seeds}"
    )
    print(format_table(results))
    return 0


def cmd_frontier(args: argparse.Namespace) -> int:
    env = _env_from_args(args)
    lams = [float(x) for x in args.lams.split(",")]
    controllers: list[Controller] = [
        FixedCadenceController(period=1, alpha=0.1),
        FixedCadenceController(period=5, alpha=0.5),
        FixedCadenceController(period=20, alpha=1.0),
        LyapunovController(n_fit=args.n_fit),
    ]
    controllers += [DriftPlusPenaltyController(n_fit=args.n_fit, lam=lam) for lam in lams]
    results = run_benchmark(controllers, env, args.steps, args.n_fit, args.probe_size, args.seeds)
    results.sort(key=lambda r: r.mean_real_samples)
    print(
        f"environment: drift={env.drift}  steps={args.steps}  n_fit={args.n_fit}  seeds={args.seeds}"
    )
    print("sorted by real-data budget (a frontier: mean V should fall as budget rises)")
    print(format_table(results))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lrcctl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="version and overview").set_defaults(func=cmd_info)

    p_run = sub.add_parser("run", help="run one closed-loop episode")
    _add_env_args(p_run)
    p_run.add_argument(
        "--controller", choices=["lyapunov", "dpp", "fixed", "never"], default="lyapunov"
    )
    p_run.add_argument("--eta", type=float, default=0.3)
    p_run.add_argument("--lam", type=float, default=2e-4)
    p_run.add_argument("--period", type=int, default=5)
    p_run.add_argument("--alpha", type=float, default=0.5)
    p_run.add_argument("--beta", type=float, default=0.0)
    p_run.add_argument("--seed", type=int, default=0)
    p_run.set_defaults(func=cmd_run)

    p_bench = sub.add_parser("benchmark", help="controllers vs fixed-cadence baselines")
    _add_env_args(p_bench)
    p_bench.add_argument("--eta", type=float, default=0.3)
    p_bench.add_argument("--lam", type=float, default=2e-4)
    p_bench.add_argument("--seeds", type=int, default=20)
    p_bench.set_defaults(func=cmd_benchmark)

    p_front = sub.add_parser("frontier", help="lam sweep: cost-stability Pareto frontier")
    _add_env_args(p_front)
    p_front.add_argument("--lams", default="1e-3,5e-4,2e-4,1e-4,5e-5")
    p_front.add_argument("--seeds", type=int, default=10)
    p_front.set_defaults(func=cmd_frontier)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
