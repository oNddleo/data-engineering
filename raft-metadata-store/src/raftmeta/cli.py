"""CLI for raft-metadata-store."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_demo(args: argparse.Namespace) -> int:
    from raftmeta.store import MetadataStore

    store = MetadataStore(
        node_ids=[f"n{i}" for i in range(args.nodes)],
        seed=args.seed,
    )
    print(json.dumps({"leader": store.leader, "status": "elected"}))

    for i in range(args.writes):
        key, val = f"key{i}", f"val{i}"
        store.set(key, val)

    result = {
        "leader": store.leader,
        "keys": store.keys(),
        "sample_read": store.get("key0"),
    }
    print(json.dumps(result))
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    import sys

    from raftmeta.io_jsonl import write_snapshot
    from raftmeta.store import MetadataStore

    store = MetadataStore(node_ids=[f"n{i}" for i in range(args.nodes)], seed=args.seed)
    for i in range(args.writes):
        store.set(f"k{i}", f"v{i}")
    write_snapshot(store.cluster.nodes, sys.stdout)  # type: ignore[arg-type]
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="raftmeta",
        description="Raft metadata store — stdlib-only Raft consensus simulation",
    )
    sub = p.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run a quick cluster demo")
    demo.add_argument("--nodes", type=int, default=3)
    demo.add_argument("--writes", type=int, default=5)
    demo.add_argument("--seed", type=int, default=42)

    snap = sub.add_parser("snapshot", help="Dump cluster state as JSONL")
    snap.add_argument("--nodes", type=int, default=3)
    snap.add_argument("--writes", type=int, default=5)
    snap.add_argument("--seed", type=int, default=42)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "demo": _cmd_demo,
        "snapshot": _cmd_snapshot,
    }
    code = dispatch[args.command](args)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
