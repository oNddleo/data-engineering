"""``partitioner`` CLI: info | hash | range | consistent | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from partitioner.consistent import ConsistentHashRing
from partitioner.hash_mod import HashModPartitioner
from partitioner.io_jsonl import dump_assignments, dump_keys, load_keys
from partitioner.range_part import RangePartitioner
from partitioner.simulator import generate_keys


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "partitioner-toolkit",
                "version": "0.1.0",
                "subcommands": ["info", "hash", "range", "consistent", "simulate"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_hash(ns: argparse.Namespace) -> int:
    p = HashModPartitioner(ns.partitions)
    keys = load_keys(Path(ns.input).read_text(encoding="utf-8"))
    pairs = [(k, p.partition_for(k)) for k in keys]
    Path(ns.output).write_text(dump_assignments(pairs), encoding="utf-8")
    counts: dict[int, int] = {}
    for _, part in pairs:
        counts[part] = counts.get(part, 0) + 1
    print(json.dumps({"n_keys": len(keys), "partitions": ns.partitions, "counts": counts}))
    return 0


def _cmd_range(ns: argparse.Namespace) -> int:
    boundaries = [int(b) for b in ns.boundaries.split(",")]
    p = RangePartitioner(boundaries)
    print(
        json.dumps(
            {
                "boundaries": p.boundaries,
                "n_partitions": p.n_partitions,
                "sample": {str(k): p.partition_for(k) for k in ns.keys},
            }
        )
    )
    return 0


def _cmd_consistent(ns: argparse.Namespace) -> int:
    ring = ConsistentHashRing(ns.nodes, replicas=ns.replicas)
    keys = load_keys(Path(ns.input).read_text(encoding="utf-8"))
    assignments: dict[str, list[str]] = {n: [] for n in ns.nodes}
    for k in keys:
        assignments[ring.node_for(k)].append(k)
    counts = {n: len(v) for n, v in assignments.items()}
    Path(ns.output).write_text(
        "\n".join(
            json.dumps({"key": k, "node": ring.node_for(k)}, ensure_ascii=False) for k in keys
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"n_keys": len(keys), "counts": counts}))
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    keys = generate_keys(n=ns.n, alphabet_size=ns.alphabet, seed=ns.seed)
    Path(ns.output).write_text(dump_keys(keys), encoding="utf-8")
    print(json.dumps({"count": len(keys), "output": ns.output}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="partitioner")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    h = sub.add_parser("hash")
    h.add_argument("--input", required=True)
    h.add_argument("--output", required=True)
    h.add_argument("--partitions", type=int, required=True)
    h.set_defaults(func=_cmd_hash)

    r = sub.add_parser("range")
    r.add_argument("--boundaries", required=True, help="comma-separated, ascending")
    r.add_argument("keys", type=int, nargs="+")
    r.set_defaults(func=_cmd_range)

    c = sub.add_parser("consistent")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--nodes", nargs="+", required=True)
    c.add_argument("--replicas", type=int, default=128)
    c.set_defaults(func=_cmd_consistent)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=1000)
    sim.add_argument("--alphabet", type=int, default=1000)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
