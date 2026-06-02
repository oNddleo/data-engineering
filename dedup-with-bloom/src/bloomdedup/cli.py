"""``bloomdedup`` CLI: info | params | dedup | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bloomdedup.dedup import dedup_stream
from bloomdedup.io_jsonl import dump_keys, load_keys
from bloomdedup.schema import BloomParams
from bloomdedup.simulator import generate


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "dedup-with-bloom",
                "version": "0.1.0",
                "subcommands": ["info", "params", "dedup", "simulate"],
            },
            indent=2,
        ),
    )
    return 0


def _cmd_params(ns: argparse.Namespace) -> int:
    p = BloomParams.for_capacity(ns.capacity, fpr=ns.fpr)
    print(
        json.dumps(
            {
                "capacity": p.capacity,
                "fpr": p.fpr,
                "m_bits": p.m_bits,
                "m_bytes": p.m_bytes,
                "k_hashes": p.k_hashes,
            }
        )
    )
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    keys = generate(
        n=ns.n,
        n_unique=ns.unique,
        duplicate_rate=ns.duplicate_rate,
        seed=ns.seed,
    )
    Path(ns.output).write_text(dump_keys(keys), encoding="utf-8")
    print(json.dumps({"count": len(keys), "output": ns.output}))
    return 0


def _cmd_dedup(ns: argparse.Namespace) -> int:
    keys = load_keys(Path(ns.input).read_text(encoding="utf-8"))
    kept, stats = dedup_stream(keys, capacity=ns.capacity, fpr=ns.fpr)
    Path(ns.output).write_text(dump_keys(kept), encoding="utf-8")
    print(
        json.dumps(
            {
                "seen": stats.seen,
                "kept": stats.kept,
                "suppressed": stats.suppressed,
                "suppression_rate": round(stats.suppression_rate, 4),
            }
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bloomdedup")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    params = sub.add_parser("params")
    params.add_argument("--capacity", type=int, required=True)
    params.add_argument("--fpr", type=float, default=0.01)
    params.set_defaults(func=_cmd_params)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=10_000)
    sim.add_argument("--unique", type=int, default=1_000)
    sim.add_argument("--duplicate-rate", type=float, default=0.5)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    dedup = sub.add_parser("dedup")
    dedup.add_argument("--input", required=True)
    dedup.add_argument("--output", required=True)
    dedup.add_argument("--capacity", type=int, default=100_000)
    dedup.add_argument("--fpr", type=float, default=0.01)
    dedup.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
