"""``idemp`` CLI: info | fingerprint | simulate-run."""

from __future__ import annotations

import argparse
import json
import sys

from idempotency.schema import EntryStatus, fingerprint
from idempotency.simulator import generate
from idempotency.store import IdempotencyStore, Outcome


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "idempotency-key-store",
                "version": "0.1.0",
                "subcommands": ["info", "fingerprint", "simulate-run"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_fingerprint(ns: argparse.Namespace) -> int:
    print(json.dumps({"payload": ns.payload, "fingerprint": fingerprint(ns.payload)}))
    return 0


def _cmd_simulate_run(ns: argparse.Namespace) -> int:
    """Generate a request stream, push through the store, report stats."""
    store = IdempotencyStore()
    requests = generate(
        n_unique=ns.unique,
        n_total=ns.total,
        seed=ns.seed,
    )
    counts: dict[str, int] = {o.value: 0 for o in Outcome}
    for req in requests:
        fp = fingerprint(req.payload)
        result = store.check_or_reserve(
            key=req.key,
            request_fingerprint=fp,
            now_ms=req.arrived_at_ms,
            ttl_ms=ns.ttl_ms,
        )
        counts[result.outcome.value] += 1
        if result.outcome == Outcome.NEW:
            store.finalize(
                key=req.key,
                response_body=f'{{"ok":true,"key":"{req.key}"}}',
                status=EntryStatus.SUCCEEDED,
                now_ms=req.arrived_at_ms,
            )
    print(
        json.dumps(
            {
                "n_requests": len(requests),
                "n_unique_keys": ns.unique,
                "outcomes": counts,
                "store_size": len(store),
            }
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="idemp")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    fp = sub.add_parser("fingerprint")
    fp.add_argument("payload")
    fp.set_defaults(func=_cmd_fingerprint)

    sim = sub.add_parser("simulate-run")
    sim.add_argument("--unique", type=int, default=100)
    sim.add_argument("--total", type=int, default=500)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--ttl-ms", type=int, default=24 * 3600 * 1000)
    sim.set_defaults(func=_cmd_simulate_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
