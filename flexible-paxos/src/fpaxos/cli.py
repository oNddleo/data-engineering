from __future__ import annotations

import argparse
import sys

from fpaxos.acceptor import Acceptor
from fpaxos.proposer import Proposer
from fpaxos.quorum import QuorumManager
from fpaxos.transport import InMemoryTransport
from fpaxos.types import QuorumConfig


def _build_cluster(n: int) -> tuple[InMemoryTransport, list[Acceptor]]:
    transport = InMemoryTransport()
    acceptors = [Acceptor(node_id=i) for i in range(n)]
    for a in acceptors:
        transport.register(a)
    return transport, acceptors


def _cmd_demo(args: argparse.Namespace) -> None:
    """Run a short Flexible Paxos demo."""
    n: int = args.nodes
    q1: int = args.q1
    q2: int = args.q2

    print(f"Flexible Paxos demo: n={n}, Q1={q1}, Q2={q2}")

    try:
        config = QuorumConfig(n=n, q1=q1, q2=q2)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    transport, _ = _build_cluster(n)
    proposer = Proposer(proposer_id=0, transport=transport)

    value = args.value
    print(f"Proposing value: {value!r}")

    try:
        decided = proposer.propose(value, config)
        print(f"Decided: {decided!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"Consensus failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_quorum(args: argparse.Namespace) -> None:
    """Show quorum recommendations for a given cluster size and workload."""
    n: int = args.nodes
    write_ratio: float = args.write_ratio

    if not 0.0 <= write_ratio <= 1.0:
        print("ERROR: write-ratio must be between 0 and 1", file=sys.stderr)
        sys.exit(1)

    manager = QuorumManager(n)
    # Simulate synthetic workload
    writes = int(write_ratio * 100)
    reads = 100 - writes
    for _ in range(writes):
        manager.record_write()
    for _ in range(reads):
        manager.record_read()

    cfg = manager.get_config()
    print(f"n={n}, write_ratio={write_ratio:.2f}")
    print(f"Recommended: Q1={cfg.q1}, Q2={cfg.q2}  (Q1+Q2={cfg.q1+cfg.q2} > {n})")

    if write_ratio >= 0.7:
        print("Profile: write-heavy → small Q2 optimises write latency")
    elif write_ratio <= 0.3:
        print("Profile: read-heavy  → small Q1 optimises leader election")
    else:
        print("Profile: balanced    → majority quorums")


def main() -> None:
    """Entry-point for the *fpaxos* CLI."""
    parser = argparse.ArgumentParser(
        prog="fpaxos",
        description="Flexible Paxos — demo and quorum advisor",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- demo subcommand ----
    p_demo = sub.add_parser("demo", help="Run a single-round consensus demo")
    p_demo.add_argument("-n", "--nodes", type=int, default=5, help="Number of acceptors")
    p_demo.add_argument("--q1", type=int, default=3, help="Phase-1 quorum size")
    p_demo.add_argument("--q2", type=int, default=3, help="Phase-2 quorum size")
    p_demo.add_argument("-v", "--value", default="hello", help="Value to propose")
    p_demo.set_defaults(func=_cmd_demo)

    # ---- quorum subcommand ----
    p_quorum = sub.add_parser("quorum", help="Recommend quorum sizes for a workload")
    p_quorum.add_argument("-n", "--nodes", type=int, default=5, help="Number of acceptors")
    p_quorum.add_argument(
        "--write-ratio",
        type=float,
        default=0.5,
        dest="write_ratio",
        help="Fraction of operations that are writes (0.0–1.0)",
    )
    p_quorum.set_defaults(func=_cmd_quorum)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
