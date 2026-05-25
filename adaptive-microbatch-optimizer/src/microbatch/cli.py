"""CLI entry point for the adaptive micro-batch optimizer."""

from __future__ import annotations

import argparse
import io
import json
import math
import sys

from microbatch.io_jsonl import write_snapshots
from microbatch.pid import PIDConfig
from microbatch.window import AdaptiveWindowManager, SLAConfig


def _simulate(args: argparse.Namespace) -> int:
    """Run a deterministic simulation and print window-size trace."""
    sla = SLAConfig(
        target_latency_s=args.target_latency,
        backpressure_weight=0.5,
    )
    pid = PIDConfig(kp=0.4, ki=0.05, kd=0.15)
    mgr = AdaptiveWindowManager(sla=sla, pid_config=pid, initial_window=args.initial_window)

    # Synthetic latency: starts high, decays to target, then drops below target
    n = args.steps
    rows = []
    for i in range(n):
        phase = i / max(n - 1, 1)
        # First half: latency decays from 3× target to target
        # Second half: latency hovers at 0.3× target
        if phase < 0.5:
            lat = args.target_latency * (3.0 - 4.0 * phase)
        else:
            lat = args.target_latency * 0.3
        w = mgr.after_batch(batch_size=100, processing_time_s=lat)
        rows.append({"step": i, "window_s": round(w, 4), "latency_s": round(lat, 4)})
        if not args.quiet:
            print(f"step={i:3d}  window={w:.3f}s  latency={lat:.3f}s")

    if args.output:
        import pathlib

        pathlib.Path(args.output).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        print(f"Wrote {len(rows)} rows → {args.output}")

    if args.snapshot:
        snaps = mgr.history()
        buf = io.StringIO()
        write_snapshots(snaps, buf)
        import pathlib

        pathlib.Path(args.snapshot).write_text(buf.getvalue())
        print(f"Wrote {len(snaps)} snapshots → {args.snapshot}")

    return 0


def _summary(args: argparse.Namespace) -> int:
    """Print summary stats from a simulation JSONL trace."""
    import pathlib

    path = pathlib.Path(args.trace)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if not rows:
        print("No rows in trace.", file=sys.stderr)
        return 1

    windows = [r["window_s"] for r in rows if "window_s" in r]
    latencies = [r["latency_s"] for r in rows if "latency_s" in r]

    def _stats(vals: list[float]) -> dict[str, float]:
        n = len(vals)
        if n == 0:
            return {}
        s = sorted(vals)
        return {
            "n": n,
            "min": s[0],
            "max": s[-1],
            "mean": sum(vals) / n,
            "p50": s[n // 2],
            "p95": s[math.ceil(0.95 * n) - 1],
        }

    print("=== window_s ===")
    for k, v in _stats(windows).items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print("=== latency_s ===")
    for k, v in _stats(latencies).items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="microbatch",
        description="Adaptive micro-batch optimizer — PID-driven window sizing",
    )
    sub = parser.add_subparsers(dest="command")

    p_sim = sub.add_parser("simulate", help="Run a deterministic simulation")
    p_sim.add_argument("--steps", type=int, default=60)
    p_sim.add_argument("--target-latency", type=float, default=0.2)
    p_sim.add_argument("--initial-window", type=float, default=0.5)
    p_sim.add_argument("--output", help="Write trace JSONL to this path")
    p_sim.add_argument("--snapshot", help="Write window snapshots to this path")
    p_sim.add_argument("--quiet", action="store_true")

    p_sum = sub.add_parser("summary", help="Summarise a simulation trace")
    p_sum.add_argument("trace", help="Path to JSONL trace file")

    args = parser.parse_args(argv)
    dispatch = {"simulate": _simulate, "summary": _summary}
    fn = dispatch.get(args.command or "")
    if fn is None:
        parser.print_help()
        return
    code = fn(args)
    if code:
        sys.exit(code)
