"""CLI for the CRDT composition algebra."""

from __future__ import annotations

import argparse
import json
import sys

from crdt.crdts import GCounter, GSet, ORSet, PNCounter


def _demo(args: argparse.Namespace) -> int:
    """Show CRDTs merging across simulated nodes."""
    n = args.nodes
    if not args.quiet:
        print(f"=== GCounter ({n} nodes) ===")
    # Each node increments once
    counters = [GCounter.new().increment(f"n{i}") for i in range(n)]
    merged: GCounter = counters[0]
    for c in counters[1:]:
        merged = merged.merge(c)
    if not args.quiet:
        print(f"  merged value = {merged.value()} (expected {n})")

    if not args.quiet:
        print(f"=== PNCounter ({n} nodes) ===")
    pn = PNCounter.new()
    for i in range(n):
        pn = pn.increment(f"n{i}")
    for i in range(0, n // 2):
        pn = pn.decrement(f"n{i}")
    expected_pn = n - n // 2
    if not args.quiet:
        print(f"  value = {pn.value()} (expected {expected_pn})")

    if not args.quiet:
        print("=== ORSet (add-wins) ===")
    s1 = ORSet.new().add("x", "n0").add("y", "n0")
    s2 = ORSet.new().add("x", "n1")
    s2 = s2.remove("x")  # n1 removes x (concurrent with n0's add)
    merged_set = s1.merge(s2)
    # n0's add of x happened after n1 had no x, so x survives in n0's view
    # After merge: x is present (n0 added it after n1's remove of its own token)
    if not args.quiet:
        print(f"  elements after add-wins merge: {sorted(merged_set.elements())}")

    if args.output:
        import pathlib

        snap = [
            {"crdt": "GCounter", "nodes": n, "value": merged.value()},
            {"crdt": "PNCounter", "nodes": n, "value": pn.value()},
            {"crdt": "ORSet", "elements": sorted(merged_set.elements())},
        ]
        pathlib.Path(args.output).write_text("\n".join(json.dumps(s) for s in snap) + "\n")
        print(f"Wrote snapshot → {args.output}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    """Verify semilattice laws for each CRDT type."""
    import random

    rng = random.Random(args.seed)
    errors: list[str] = []

    def check(name: str, a: object, b: object, c: object) -> None:
        from crdt.lattice import Lattice

        if not isinstance(a, Lattice) or not isinstance(b, Lattice) or not isinstance(c, Lattice):
            return
        ab = a.merge(b)
        ba = b.merge(a)
        if ab != ba:
            errors.append(f"{name}: not commutative")
        aa = a.merge(a)
        if aa != a:
            errors.append(f"{name}: not idempotent")
        abc = a.merge(b).merge(c)
        abc2 = a.merge(b.merge(c))
        if abc != abc2:
            errors.append(f"{name}: not associative")

    # GCounter
    for _ in range(args.rounds):
        a = GCounter({"n0": rng.randint(0, 10), "n1": rng.randint(0, 10)})
        b = GCounter({"n0": rng.randint(0, 10), "n2": rng.randint(0, 10)})
        c = GCounter({"n1": rng.randint(0, 10), "n2": rng.randint(0, 10)})
        check("GCounter", a, b, c)

    # PNCounter
    for _ in range(args.rounds):
        ia = GCounter({"n0": rng.randint(0, 5)})
        da = GCounter({"n0": rng.randint(0, 3)})
        ib = GCounter({"n1": rng.randint(0, 5)})
        db = GCounter({"n1": rng.randint(0, 3)})
        ic = GCounter({"n2": rng.randint(0, 5)})
        dc = GCounter({"n2": rng.randint(0, 3)})
        check("PNCounter", PNCounter(ia, da), PNCounter(ib, db), PNCounter(ic, dc))

    # GSet
    for _ in range(args.rounds):
        elems = ["a", "b", "c", "d", "e"]
        a_gs = GSet(frozenset(rng.sample(elems, rng.randint(0, 3))))
        b_gs = GSet(frozenset(rng.sample(elems, rng.randint(0, 3))))
        c_gs = GSet(frozenset(rng.sample(elems, rng.randint(0, 3))))
        check("GSet", a_gs, b_gs, c_gs)

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    total = args.rounds * 3
    if not args.quiet:
        print(f"All {total} law checks passed (idempotent, commutative, associative).")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="crdt",
        description="CRDT composition algebra — semilattice-based distributed data types",
    )
    sub = parser.add_subparsers(dest="command")

    p_demo = sub.add_parser("demo", help="Show CRDTs merging across simulated nodes")
    p_demo.add_argument("--nodes", type=int, default=4)
    p_demo.add_argument("--output", help="Write snapshot JSONL to this path")
    p_demo.add_argument("--quiet", action="store_true")

    p_ver = sub.add_parser("verify", help="Verify semilattice laws")
    p_ver.add_argument("--rounds", type=int, default=100)
    p_ver.add_argument("--seed", type=int, default=42)
    p_ver.add_argument("--quiet", action="store_true")

    args = parser.parse_args(argv)
    dispatch = {"demo": _demo, "verify": _verify}
    fn = dispatch.get(args.command or "")
    if fn is None:
        parser.print_help()
        return
    code = fn(args)
    if code:
        sys.exit(code)
