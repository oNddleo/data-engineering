"""``scdkit`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from scdkit import __version__

    print(f"slowly-changing-dimensions-toolkit {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from scdkit.io_jsonl import snapshot_to_lines
    from scdkit.simulator import generate_pair

    before, after = generate_pair(
        n_entities=args.entities,
        insert_fraction=args.insert_fraction,
        delete_fraction=args.delete_fraction,
        update_fraction=args.update_fraction,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "before.jsonl").write_text(snapshot_to_lines(before), encoding="utf-8")
    (out_dir / "after.jsonl").write_text(snapshot_to_lines(after), encoding="utf-8")
    print(
        f"wrote {len(before)} entities (before) + {len(after)} entities (after) to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    from scdkit.detect import detect, n_changes_by_kind
    from scdkit.io_jsonl import dump_changes, snapshot_from_text

    before = snapshot_from_text(Path(args.before).read_text(encoding="utf-8"))
    after = snapshot_from_text(Path(args.after).read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(args.as_of)
    tracked = args.tracked_attrs.split(",") if args.tracked_attrs else None
    changes = detect(before, after, as_of=as_of, tracked_attrs=tracked)
    if args.output:
        Path(args.output).write_text(dump_changes(changes), encoding="utf-8")
        print(f"wrote {len(changes)} changes to {args.output}", file=sys.stderr)
    counts = n_changes_by_kind(changes)
    print("Changes by kind:")
    for kind, n in counts.items():
        print(f"  {kind.value:<8} {n:>5}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    from scdkit.appliers import (
        apply_type_1,
        apply_type_2,
        apply_type_3,
        apply_type_4,
        apply_type_6,
        type_2_empty,
        type_4_empty,
        type_6_empty,
    )
    from scdkit.io_jsonl import dump_rows, load_changes
    from scdkit.schema import SCDType

    changes = list(load_changes(Path(args.changes).read_text(encoding="utf-8")))
    scd_type = SCDType(args.type)
    tracked = args.tracked_attrs.split(",") if args.tracked_attrs else ["shop_name", "tier"]

    if scd_type is SCDType.TYPE_1:
        result_t1 = apply_type_1({}, changes)
        rows = sorted(result_t1.values(), key=lambda r: r.natural_key)
    elif scd_type is SCDType.TYPE_2:
        state_t2 = apply_type_2(type_2_empty(), changes)
        rows = sorted(
            state_t2.rows.values(),
            key=lambda r: (r.natural_key, r.surrogate_key or 0),
        )
    elif scd_type is SCDType.TYPE_3:
        result_t3 = apply_type_3({}, changes, tracked_attrs=tracked)
        rows = sorted(result_t3.values(), key=lambda r: r.natural_key)
    elif scd_type is SCDType.TYPE_4:
        from scdkit.schema import VN_TZ

        state_t4 = apply_type_4(type_4_empty(), changes)
        far_past = datetime.min.replace(tzinfo=VN_TZ)
        rows = sorted(state_t4.current.values(), key=lambda r: r.natural_key)
        rows += sorted(
            state_t4.history,
            key=lambda r: (r.natural_key, r.effective_from or far_past),
        )
    else:  # TYPE_6
        state_t6 = apply_type_6(type_6_empty(), changes, tracked_attrs=tracked)
        rows = sorted(state_t6.current.values(), key=lambda r: r.natural_key)

    out_text = dump_rows(rows)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"wrote {len(rows)} rows ({scd_type.value}) to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Show Type-2 history for one entity."""
    from scdkit.appliers import apply_type_2, type_2_empty, type_2_history_for
    from scdkit.io_jsonl import load_changes

    changes = list(load_changes(Path(args.changes).read_text(encoding="utf-8")))
    state = apply_type_2(type_2_empty(), changes)
    history = type_2_history_for(state, args.natural_key)
    if not history:
        print(f"no history for {args.natural_key}", file=sys.stderr)
        return 1
    print(f"{'sk':>4} {'from':<25} {'to':<25} {'current':>7} attributes")
    for r in history:
        from_s = r.effective_from.isoformat() if r.effective_from else "—"
        to_s = r.effective_to.isoformat() if r.effective_to else "—"
        attrs = json.dumps(r.attributes, ensure_ascii=False, sort_keys=True)
        print(
            f"{r.surrogate_key or 0:>4} {from_s:<25} {to_s:<25} "
            f"{'YES' if r.is_current else 'NO':>7} {attrs}"
        )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from scdkit.detect import detect, n_changes_by_kind
    from scdkit.io_jsonl import snapshot_from_text

    before = snapshot_from_text(Path(args.before).read_text(encoding="utf-8"))
    after = snapshot_from_text(Path(args.after).read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(args.as_of)
    changes = detect(before, after, as_of=as_of)
    counts = n_changes_by_kind(changes)
    payload = {
        "n_before": len(before),
        "n_after": len(after),
        "n_changes": len(changes),
        "by_kind": {k.value: v for k, v in counts.items()},
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="scdkit",
        description="Slowly-Changing Dimensions toolkit — detect changes, apply Type 1/2/3/4/6.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="generate before/after snapshot pair")
    sim.add_argument("--entities", type=int, default=50)
    sim.add_argument("--insert-fraction", type=float, default=0.10)
    sim.add_argument("--delete-fraction", type=float, default=0.05)
    sim.add_argument("--update-fraction", type=float, default=0.30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    dt = sub.add_parser("detect", help="diff before vs after into DimensionChange events")
    dt.add_argument("--before", required=True)
    dt.add_argument("--after", required=True)
    dt.add_argument("--as-of", required=True, help="ISO timestamp tag for emitted change events")
    dt.add_argument(
        "--tracked-attrs", default="", help="comma-separated attrs to track (default: all)"
    )
    dt.add_argument("--output", default=None)
    dt.set_defaults(func=cmd_detect)

    ap = sub.add_parser("apply", help="apply changes under a chosen SCD type")
    ap.add_argument(
        "--type", required=True, choices=["TYPE_1", "TYPE_2", "TYPE_3", "TYPE_4", "TYPE_6"]
    )
    ap.add_argument("--changes", required=True)
    ap.add_argument(
        "--tracked-attrs",
        default="",
        help="for TYPE_3/TYPE_6: which attrs get previous_value tracking",
    )
    ap.add_argument("--output", default=None)
    ap.set_defaults(func=cmd_apply)

    hs = sub.add_parser("history", help="show Type-2 history for one entity")
    hs.add_argument("--changes", required=True)
    hs.add_argument("--natural-key", required=True)
    hs.set_defaults(func=cmd_history)

    sm = sub.add_parser("summary", help="JSON summary of detected changes")
    sm.add_argument("--before", required=True)
    sm.add_argument("--after", required=True)
    sm.add_argument("--as-of", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
