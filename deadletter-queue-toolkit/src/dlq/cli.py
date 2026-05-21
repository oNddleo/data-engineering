"""``dlq`` CLI: info | classify | backoff | summarize | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dlq.io_jsonl import dump, load
from dlq.queue import DeadLetterQueue
from dlq.retry import JitterMode, RetryPolicy, next_backoff_ms
from dlq.schema import classify
from dlq.simulator import generate


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "deadletter-queue-toolkit",
                "version": "0.1.0",
                "subcommands": [
                    "info",
                    "classify",
                    "backoff",
                    "summarize",
                    "simulate",
                ],
            },
            indent=2,
        )
    )
    return 0


def _cmd_classify(ns: argparse.Namespace) -> int:
    print(json.dumps({"error": ns.error, "kind": classify(ns.error).value}))
    return 0


def _cmd_backoff(ns: argparse.Namespace) -> int:
    import random as _rand

    policy = RetryPolicy(
        max_attempts=ns.max_attempts,
        base_ms=ns.base_ms,
        multiplier=ns.multiplier,
        max_backoff_ms=ns.max_backoff_ms,
        jitter=JitterMode(ns.jitter),
    )
    rng = _rand.Random(ns.seed)
    schedule = [next_backoff_ms(policy, a, rng=rng) for a in range(ns.max_attempts)]
    print(json.dumps({"max_attempts": ns.max_attempts, "schedule_ms": schedule}))
    return 0


def _cmd_summarize(ns: argparse.Namespace) -> int:
    items = load(Path(ns.input).read_text(encoding="utf-8"))
    q = DeadLetterQueue()
    q.extend(items)
    counts = {k.value: v for k, v in q.counts_by_kind().items()}
    topics: dict[str, int] = {}
    for dl in items:
        topics[dl.original_topic] = topics.get(dl.original_topic, 0) + 1
    print(json.dumps({"total": len(items), "by_kind": counts, "by_topic": topics}))
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    items = generate(n=ns.n, seed=ns.seed)
    Path(ns.output).write_text(dump(items), encoding="utf-8")
    print(json.dumps({"count": len(items), "output": ns.output}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dlq")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    cls = sub.add_parser("classify")
    cls.add_argument("error", help="error message to bucket")
    cls.set_defaults(func=_cmd_classify)

    bo = sub.add_parser("backoff")
    bo.add_argument("--max-attempts", type=int, default=5)
    bo.add_argument("--base-ms", type=int, default=100)
    bo.add_argument("--multiplier", type=float, default=2.0)
    bo.add_argument("--max-backoff-ms", type=int, default=30_000)
    bo.add_argument("--jitter", choices=["none", "full", "equal"], default="full")
    bo.add_argument("--seed", type=int, default=0)
    bo.set_defaults(func=_cmd_backoff)

    sm = sub.add_parser("summarize")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=_cmd_summarize)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=50)
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
