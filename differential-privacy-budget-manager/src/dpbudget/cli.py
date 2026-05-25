"""CLI for the differential-privacy budget manager."""

from __future__ import annotations

import argparse
import sys


def _demo(args: argparse.Namespace) -> int:
    from dpbudget.simulator import run_demo  # noqa: TCH001

    gw = run_demo()
    log = gw.audit_log()
    if not args.quiet:
        allowed = sum(1 for e in log if e.status.value == "allowed")
        blocked = sum(1 for e in log if e.status.value == "blocked")
        print(f"Queries executed : {len(log)}")
        print(f"  allowed        : {allowed}")
        print(f"  blocked        : {blocked}")
        print()
        for e in log:
            tag = "✓" if e.status.value == "allowed" else "✗"
            noisy = f"{e.noisy_result:.2f}" if e.noisy_result is not None else "—"
            print(
                f"  [{tag}] {e.analyst_id}/{e.dataset_id}"
                f"  ε={e.epsilon_consumed:.3f}  result={noisy}"
            )

    if args.output:
        import io
        import pathlib

        from dpbudget.io_jsonl import write_log  # noqa: TCH001

        buf = io.StringIO()
        write_log(log, buf)
        pathlib.Path(args.output).write_text(buf.getvalue())
        print(f"Wrote audit log → {args.output}")

    return 0


def _query(args: argparse.Namespace) -> int:
    from dpbudget.mechanisms import apply_laplace  # noqa: TCH001

    true_val = float(args.true_value)
    eps = float(args.epsilon)
    sens = float(args.sensitivity)
    noisy, noise = apply_laplace(true_val, sens, eps)
    print(f"true={true_val}  ε={eps}  sensitivity={sens}")
    print(f"noise added : {noise:+.6f}")
    print(f"noisy result: {noisy:.6f}")
    return 0


def _compose(args: argparse.Namespace) -> int:
    from dpbudget.composition import (  # noqa: TCH001
        advanced_compose_epsilon,
        basic_compose_epsilon,
    )

    epsilons = [float(e) for e in args.epsilons]
    basic = basic_compose_epsilon(epsilons)
    delta = float(args.delta)
    adv = advanced_compose_epsilon(epsilons, delta)
    print(f"Composing {len(epsilons)} mechanisms: {epsilons}")
    print(f"  Basic composition ε    : {basic:.6f}")
    print(f"  Advanced composition ε : {adv:.6f}  (δ'={delta})")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="dpbudget",
        description="Differential-privacy budget manager",
    )
    sub = parser.add_subparsers(dest="command")

    p_demo = sub.add_parser("demo", help="Run multi-analyst demo")
    p_demo.add_argument("--quiet", action="store_true")
    p_demo.add_argument("--output", help="Write audit log JSONL to this path")

    p_q = sub.add_parser("query", help="Apply Laplace noise to a single value")
    p_q.add_argument("true_value", type=float)
    p_q.add_argument("--epsilon", type=float, default=1.0)
    p_q.add_argument("--sensitivity", type=float, default=1.0)

    p_c = sub.add_parser("compose", help="Show composition bounds for a list of ε values")
    p_c.add_argument("epsilons", nargs="+")
    p_c.add_argument("--delta", type=float, default=1e-5)

    args = parser.parse_args(argv)
    dispatch = {"demo": _demo, "query": _query, "compose": _compose}
    fn = dispatch.get(args.command or "")
    if fn is None:
        parser.print_help()
        return
    code = fn(args)
    if code:
        sys.exit(code)
