"""``lsmmerge`` CLI: info | merge | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lsmmerge.io_jsonl import dump_records, load_records
from lsmmerge.merge import merge_runs
from lsmmerge.simulator import generate_runs


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "lsm-merge-iterator",
                "version": "0.1.0",
                "subcommands": ["info", "merge", "simulate"],
            },
            indent=2,
        ),
    )
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    runs = generate_runs(
        n_runs=ns.n_runs,
        keys_per_run=ns.keys_per_run,
        key_universe=ns.key_universe,
        tombstone_rate=ns.tombstone_rate,
        seed=ns.seed,
    )
    out = Path(ns.output)
    out.mkdir(parents=True, exist_ok=True)
    for i, run in enumerate(runs):
        (out / f"run-{i:03d}.jsonl").write_text(dump_records(run), encoding="utf-8")
    print(json.dumps({"runs": len(runs), "output_dir": str(out)}))
    return 0


def _cmd_merge(ns: argparse.Namespace) -> int:
    in_dir = Path(ns.input)
    runs = [load_records(p.read_text(encoding="utf-8")) for p in sorted(in_dir.glob("*.jsonl"))]
    merged = list(merge_runs(runs, keep_tombstones=ns.keep_tombstones))
    Path(ns.output).write_text(dump_records(merged), encoding="utf-8")
    print(json.dumps({"input_runs": len(runs), "output_records": len(merged)}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lsmmerge")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n-runs", type=int, default=3)
    sim.add_argument("--keys-per-run", type=int, default=20)
    sim.add_argument("--key-universe", type=int, default=50)
    sim.add_argument("--tombstone-rate", type=float, default=0.1)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    mg = sub.add_parser("merge")
    mg.add_argument("--input", required=True, help="directory of run-*.jsonl files")
    mg.add_argument("--output", required=True)
    mg.add_argument("--keep-tombstones", action="store_true")
    mg.set_defaults(func=_cmd_merge)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
