"""``cdc`` CLI — simulate, replay, compact, diff, lineage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from cdc import __version__

    print(f"change-data-capture {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from cdc.io_jsonl import dump_events
    from cdc.simulator import generate

    events = generate(
        n_customers=args.customers,
        n_orders=args.orders,
        delete_fraction=args.delete_fraction,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_events(events), encoding="utf-8")
        print(f"wrote {len(events)} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_events(events))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from cdc.io_jsonl import load_events
    from cdc.replay import replay, replay_unordered

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    snapshot = (
        replay_unordered(events, strict=False)
        if args.unordered
        else replay(events, strict=not args.lenient)
    )
    payload = {
        "n_rows": len(snapshot),
        "tables": sorted({t for t, _ in snapshot}),
    }
    if args.show:
        sample = list(snapshot.items())[: args.show]
        payload["sample"] = [{"table": t, "pk": pk, "row": state} for (t, pk), state in sample]
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_compact(args: argparse.Namespace) -> int:
    from cdc.compact import compact, compact_to_inserts
    from cdc.io_jsonl import dump_events, load_events

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    out_events = compact_to_inserts(events) if args.to_inserts else compact(events)
    text = dump_events(out_events)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(
            f"compacted {len(events)} → {len(out_events)} events "
            f"(reduction {(1 - len(out_events) / max(1, len(events))) * 100:.1f}%)",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(text)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Print the column-level diff for every UPDATE in the input."""
    from cdc.diff import change_vector
    from cdc.io_jsonl import dump_change_vectors, load_events
    from cdc.schema import Op

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    diffs = [change_vector(e) for e in events if e.op is Op.UPDATE]
    text = dump_change_vectors(diffs)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(diffs)} diffs to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_lineage(args: argparse.Namespace) -> int:
    from cdc.io_jsonl import dump_lineage, load_events
    from cdc.lineage import build_lineage

    events = load_events(Path(args.input).read_text(encoding="utf-8"))
    rows = build_lineage(events)
    text = dump_lineage(rows)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(rows)} lineage rows to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'table':<12} {'pk':<10} {'created':>13} {'last_mod':>13} "
            f"{'updates':>8} {'deleted':>8}",
        )
        for r in rows[: args.show]:
            print(
                f"{r.table:<12} {r.pk:<10} {r.created_at_ms:>13} "
                f"{r.last_modified_at_ms:>13} {r.n_updates:>8} {r.is_deleted!s:>8}",
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cdc",
        description="Change-data-capture toolkit — replay, compact, diff, lineage.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic CDC stream")
    sim.add_argument("--customers", type=int, default=30)
    sim.add_argument("--orders", type=int, default=100)
    sim.add_argument("--delete-fraction", type=float, default=0.05)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    rp = sub.add_parser("replay", help="materialise a current snapshot")
    rp.add_argument("--input", required=True)
    rp.add_argument(
        "--unordered", action="store_true", help="sort events by position before replay"
    )
    rp.add_argument(
        "--lenient", action="store_true", help="silently drop illegal-transition events"
    )
    rp.add_argument("--show", type=int, default=0)
    rp.set_defaults(func=cmd_replay)

    cp = sub.add_parser("compact", help="keep only the latest event per PK")
    cp.add_argument("--input", required=True)
    cp.add_argument("--output", default=None)
    cp.add_argument(
        "--to-inserts", action="store_true", help="rewrite surviving UPDATEs as INSERTs"
    )
    cp.set_defaults(func=cmd_compact)

    df = sub.add_parser("diff", help="column-level diff for every UPDATE")
    df.add_argument("--input", required=True)
    df.add_argument("--output", default=None)
    df.set_defaults(func=cmd_diff)

    ln = sub.add_parser("lineage", help="per-row lifecycle aggregation")
    ln.add_argument("--input", required=True)
    ln.add_argument("--output", default=None)
    ln.add_argument("--show", type=int, default=5)
    ln.set_defaults(func=cmd_lineage)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
