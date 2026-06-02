"""CLI for the BFT stream processing engine."""

from __future__ import annotations

import argparse
import json
import sys

from bftstream.cluster import BFTCluster
from bftstream.schema import StreamRecord


def _simulate(args: argparse.Namespace) -> int:
    """Run a BFT stream simulation and report committed windows."""
    n = args.nodes
    f = args.faults
    window_size = args.window_size
    n_windows = args.windows
    byzantine = args.byzantine

    if n < 3 * f + 1:
        print(f"error: need at least 3f+1={3*f+1} nodes for f={f}", file=sys.stderr)
        return 1

    cluster = BFTCluster(n_replicas=n, f=f, window_size=window_size)

    # Make Byzantine replicas
    for byz_id in byzantine:
        if byz_id in cluster.replicas:
            cluster.make_byzantine(byz_id)
            if not args.quiet:
                print(f"Byzantine: {byz_id}")

    # Ingest records
    tick = 0.0
    for wid in range(n_windows):
        for i in range(window_size):
            record = StreamRecord(
                timestamp=tick,
                key=f"k{i % 5}",
                value=float(i + 1),
                window_id=wid,
            )
            cluster.ingest(record)
            tick += 1.0

    wins = cluster.committed_windows()
    if not args.quiet:
        for w in wins:
            agree = cluster.all_honest_agree(w.window_id)
            print(
                f"window={w.window_id}  count={w.record_count}"
                f"  sum={w.value_sum:.1f}  agree={agree}"
            )
        print(f"watermark={cluster.watermark()}  committed_windows={len(wins)}")

    if args.output:
        import pathlib

        buf = "\n".join(
            json.dumps(
                {
                    "window_id": w.window_id,
                    "record_count": w.record_count,
                    "value_sum": w.value_sum,
                    "committed": w.committed,
                    "all_agree": cluster.all_honest_agree(w.window_id),
                }
            )
            for w in wins
        )
        pathlib.Path(args.output).write_text(buf + "\n")
        print(f"Wrote {len(wins)} windows → {args.output}")

    return 0


def _summary(args: argparse.Namespace) -> int:
    """Summarise a committed-windows JSONL file."""
    import pathlib

    path = pathlib.Path(args.windows_file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if not rows:
        print("No committed windows.", file=sys.stderr)
        return 1

    agreed = sum(1 for r in rows if r.get("all_agree"))
    total_records = sum(r.get("record_count", 0) for r in rows)
    total_sum = sum(r.get("value_sum", 0.0) for r in rows)

    print(f"windows          : {len(rows)}")
    print(f"unanimous_agree  : {agreed}/{len(rows)}")
    print(f"total_records    : {total_records}")
    print(f"total_value_sum  : {total_sum:.2f}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bftstream",
        description="BFT stream — PBFT watermark consensus for streaming pipelines",
    )
    sub = parser.add_subparsers(dest="command")

    p_sim = sub.add_parser("simulate", help="Run a BFT stream simulation")
    p_sim.add_argument("--nodes", type=int, default=4)
    p_sim.add_argument("--faults", type=int, default=1)
    p_sim.add_argument("--window-size", type=int, default=10)
    p_sim.add_argument("--windows", type=int, default=3)
    p_sim.add_argument("--byzantine", nargs="*", default=[])
    p_sim.add_argument("--output", help="Write committed windows JSONL to this path")
    p_sim.add_argument("--quiet", action="store_true")

    p_sum = sub.add_parser("summary", help="Summarise a committed-windows JSONL file")
    p_sum.add_argument("windows_file")

    args = parser.parse_args(argv)
    dispatch = {"simulate": _simulate, "summary": _summary}
    fn = dispatch.get(args.command or "")
    if fn is None:
        parser.print_help()
        return
    code = fn(args)
    if code:
        sys.exit(code)
